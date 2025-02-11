from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator, Optional
import functools

import matplotlib.pyplot as plt

type Store = str
type Name = str
type Ingredient = str
type Pizza = frozenset[Ingredient]

ingr_common_limit = 10
with_duplicates = True


class CheckFormat:
    result: list[str]

    def __init__(self, pizzadir):
        self.result = []
        for p in Path(pizzadir).iterdir():
            with open(p) as f:
                for i, pizza in enumerate(f.read().splitlines(), start=1):
                    try:
                        name, ingr = pizza.split(":")
                    except ValueError:
                        self.result.append(f"{p}:{i}: Missing ':'")
                        continue

                    if name[0] != name[0].upper():
                        self.result.append(
                            f"{p}:{i}: Pizza name not capitalized: {name}"
                        )

                    ingrs = ingr.split(", ")
                    for ing in ingrs:
                        if ing != ing.lower():
                            self.result.append(
                                f"{p}:{i}: Ingredient name not lowercase: {ing}"
                            )

    def any_error(self):
        return len(self.result) > 0

    def report(self):
        for err in self.result:
            print(err)


class Input:
    result: dict[Store, list[Pizza]]
    names: dict[tuple[Store, Pizza], list[Name]]

    def __init__(self, pizzadir):
        self.result = {}
        self.names = defaultdict(list)
        for p in Path(pizzadir).iterdir():
            store = p.name
            self.result[store] = []
            with open(p) as f:
                for pizza in f.read().splitlines():
                    if ":" in pizza and not pizza.strip().endswith(":"):
                        name, ingr = pizza.split(":")
                        name = name.strip().lower()
                        ingr = frozenset(
                            [i.strip().lower() for i in ingr.strip().split(",")]
                        )
                    else:
                        name = pizza.strip().lower()
                        ingr = frozenset()
                    self.result[store].append(ingr)
                    self.names[(store, ingr)].append(name)

    def iter_pizzas(self) -> Iterator[tuple[Store, Pizza]]:
        yield from (
            (store, pizza) for store, pizzas in self.result.items() for pizza in pizzas
        )

    def iter_pizzas_with_names(self) -> Iterator[tuple[Store, Pizza, Name]]:
        yield from (
            (store, pizza, name)
            for store, pizzas in self.result.items()
            for pizza in pizzas
            for name in self.names[(store, pizza)]
        )


class IngredientsAtOneStore:
    result: dict[Store, set[Ingredient]]

    def __init__(self, inp: Input):
        ingr_seen_once: dict[Ingredient, Store] = {}
        ingr_seen_more: set[Ingredient] = set()

        for store, pizza in inp.iter_pizzas():
            for ingr in pizza:
                if ingr in ingr_seen_more:
                    pass
                elif ingr in ingr_seen_once and ingr_seen_once[ingr] != store:
                    ingr_seen_more.add(ingr)
                    del ingr_seen_once[ingr]
                else:
                    ingr_seen_once[ingr] = store

        self.result = {store: set() for _, store in ingr_seen_once.items()}
        for ingr, store in ingr_seen_once.items():
            self.result[store].add(ingr)

    def report(self):
        print("ingredients only used at one store:")
        for store, ingrs in self.result.items():
            print("  {}: {}".format(store, ", ".join(sorted(ingrs))))


class IngredientCount:
    counter: Counter[Ingredient]
    counter_with_duplicates: Counter[Ingredient]

    def __init__(self, inp: Input):
        self.counter = Counter()
        self.counter_with_duplicates = Counter()
        for store, pizza in inp.iter_pizzas():
            for ingr in pizza:
                self.counter[ingr] += 1
                self.counter_with_duplicates[ingr] += len(inp.names[(store, pizza)])

    def common_ingr(self, n, with_duplicates=False) -> list[Ingredient]:
        counter = self.counter_with_duplicates if with_duplicates else self.counter
        return [ingr for ingr, _ in counter.most_common(n)]


class Pizzagami:
    inp: Input
    result: dict[Store, list[tuple[Pizza, Optional[int]]]]

    def __init__(self, inp: Input, common_ingr: list[Ingredient]):
        self.inp = inp
        self._stores_with_pizza: dict[Pizza, list[Store]] = defaultdict(list)
        self._stores_with_pizza_duplicates: dict[Pizza, list[tuple[Store, Name]]] = (
            defaultdict(list)
        )
        for store, pizza in inp.iter_pizzas():
            self._stores_with_pizza[pizza].append(store)
            for name in inp.names[(store, pizza)]:
                self._stores_with_pizza_duplicates[pizza].append((store, name))

        self.result = {}
        self._pizza_per_store: dict[Store, int] = {}
        for store, pizzas in inp.result.items():
            self.result[store] = []
            self._pizza_per_store[store] = len(pizzas)

            for pizza in pizzas:
                if self.is_pizzagami(pizza):
                    is_ingr_common = all(i in common_ingr for i in pizza)
                    ingr_common_level = (
                        max(common_ingr.index(i) for i in pizza)
                        if is_ingr_common
                        else None
                    )
                    self.result[store].append((pizza, ingr_common_level))

    def count(self, pizza, with_duplicates):
        stores_with = (
            self._stores_with_pizza_duplicates
            if with_duplicates
            else self._stores_with_pizza
        )
        return len(stores_with[pizza])

    def is_pizzagami(self, pizza: Pizza):
        return self.count(pizza, with_duplicates=True) == 1

    def short_report(self):
        for store, pizzagami in self.result.items():
            if pizzagami:
                num_ingr_common_pizzagami = sum(
                    1 for gami in pizzagami if gami[1] is not None
                )
                print(
                    "{}: {} pizzagami!".format(store, len(pizzagami))
                    + " (out of {}".format(self._pizza_per_store[store])
                    + " total)"
                    + " {}%".format(
                        round(
                            len(pizzagami) * 100 / self._pizza_per_store[store],
                        )
                    )
                )
                if num_ingr_common_pizzagami:
                    print(
                        "...{} ingredient-common pizzagami".format(
                            num_ingr_common_pizzagami
                        )
                    )
            else:
                print("{}: no pizzagami :(".format(store))
            print()

    def report(self):
        for store, pizzagami in self.result.items():
            if pizzagami:
                num_ingr_common_pizzagami = sum(
                    1 for gami in pizzagami if gami[1] is not None
                )
                print(
                    "{}: {} pizzagami!".format(store, len(pizzagami))
                    + " (out of {}".format(self._pizza_per_store[store])
                    + " total)"
                )
                if num_ingr_common_pizzagami:
                    print(
                        "...{} ingredient-common pizzagami".format(
                            num_ingr_common_pizzagami
                        )
                    )

                for pizza, common_ingr_level in pizzagami:
                    names = self.inp.names[(store, pizza)]
                    if len(names) == 1:
                        name = names[0]
                    else:
                        name = "[" + ", ".join(names) + "]"
                    print("  {} ({})".format(name, ", ".join(sorted(pizza))))
                    if common_ingr_level is not None:
                        print(
                            "    {}-ingredient-common pizzagami".format(
                                common_ingr_level
                            )
                        )
            else:
                print("{}: no pizzagami :(".format(store))
            print()


class CountIngredientCommonPizzagami:
    _per_level: dict[int, int]
    _total: int

    def __init__(self, pizzagami: Pizzagami):
        self._per_level = {i: 0 for i in range(1, ingr_common_limit + 1)}
        for _, pizzagamis in pizzagami.result.items():
            for _, ingr_common_level in pizzagamis:
                if ingr_common_level is not None:
                    self._per_level[ingr_common_level] += 1
        self._total = sum(self._per_level.values())

    def report(self):
        print("{} ingredient-common pizzagami".format(self._total))
        for level in self._per_level:
            amount = sum(v for k, v in self._per_level.items() if k <= level)
            print("  {:>2}-ingredient-common pizzagami: {}".format(level, amount))


class SameThings:
    same_name: dict[Name, set[Pizza]]
    same_ingredients: dict[Pizza, set[Name]]

    def __init__(self, inp: Input):
        self.same_name = defaultdict(set)
        self.same_ingredients = defaultdict(set)
        for _, pizza, name in inp.iter_pizzas_with_names():
            self.same_name[name].add(pizza)
            self.same_ingredients[frozenset(pizza)].add(name)
        self.same_name = {
            name: pizzas for name, pizzas in self.same_name.items() if len(pizzas) > 1
        }
        self.same_ingredients = {
            pizza: names
            for pizza, names in self.same_ingredients.items()
            if len(names) > 1
        }

    def report(self):
        if self.same_name:
            print("same name, different ingredients:")
            for name, pizzas in sorted(self.same_name.items()):
                print(f"  {name}:")
                for pizza in pizzas:
                    print("    {}".format(", ".join(sorted(pizza))))
        if self.same_ingredients:
            print("same pizza, different names:")
            for pizza, names in self.same_ingredients.items():
                print("  {}:".format(", ".join(sorted(pizza))))
                for name in sorted(names):
                    print(f"    {name}")


class ConditionalProbabilityOfIngredients:
    # sorted list of P(first ingredient -> second ingredient)
    result: list[tuple[float, tuple[Ingredient, int], tuple[Ingredient, int]]]

    def __init__(self, inp: Input, min_pizzas_to_report: int):
        self.result = []
        pizzas_with: dict[Ingredient, list[Pizza]] = defaultdict(list)
        for pizza in set(pizza for _, pizza in inp.iter_pizzas()):
            for ingr in pizza:
                pizzas_with[ingr].append(pizza)
        for ingr, pizzas in sorted(pizzas_with.items()):
            if len(pizzas) < min_pizzas_to_report:
                continue
            other_ingr = set()
            for p in pizzas:
                other_ingr |= set(p)
            other_ingr.remove(ingr)
            for ingr2 in other_ingr:
                n = sum(1 for p in pizzas if ingr2 in p)
                prob = n / len(pizzas)
                self.result.append((prob, (ingr, len(pizzas)), (ingr2, n)))
        self.result.sort(reverse=True)

    def report(self, limit=30):
        for i, (p, (i1, n1), (i2, n2)) in enumerate(self.result[:limit]):
            print(f"{i+1:>3} {p:.2} {i1} ({n1}) -> {i2} ({n2})")


class FeasiblePizzas:
    # a pizza is feasible if it exists or its ingredients are a subset of a feasible pizza
    all_feasible: set[Pizza]
    not_seen: set[Pizza]

    @functools.cache
    @staticmethod
    def _all_below(pizza: Pizza) -> set[Pizza]:
        if not pizza:
            return set()
        below = {pizza}
        for i in pizza:
            below |= FeasiblePizzas._all_below(pizza - {i})
        return below

    def __init__(self, inp: Input):
        self.all_feasible = set()
        for _, pizza in inp.iter_pizzas():
            self.all_feasible |= FeasiblePizzas._all_below(pizza)
        self.not_seen = self.all_feasible - all_pizzas(inp)

    def report(self):
        p = 100 * (1.0 - (len(self.not_seen) / len(self.all_feasible)))
        print(f"{len(self.all_feasible)} feasible pizzas ({p:.1f}% seen)")


class StoreScatter:
    stores: list[tuple[int, float]]
    names: list[str]

    def __init__(self, inp: Input, pizzagami: Pizzagami):
        self.stores = []
        self.names = []
        for store, pizzas in inp.result.items():
            num_pizzagami = sum(1 for p in pizzas if pizzagami.is_pizzagami(p))
            self.stores.append((len(pizzas), num_pizzagami / len(pizzas)))
            self.names.append(store.removesuffix(".txt"))

    def figure(self):
        x, y = zip(*self.stores)
        plt.scatter(x, y)
        for i, txt in enumerate(self.names):
            plt.annotate(txt, (x[i] + 1, y[i]))
        plt.show()


class IngredientScatter:
    result: list[tuple[int, float]]
    ticks: list[str]
    labels: list[tuple[float, float, str]]

    def __init__(
        self, ingr_count: IngredientCount, cond: ConditionalProbabilityOfIngredients
    ):
        p_for_ingr: dict[Ingredient, dict[Ingredient, float]] = {
            i: {} for i in ingr_count.counter.keys()
        }
        for p, (i1, _), (i2, _) in cond.result:
            p_for_ingr[i1][i2] = p

        self.result = []
        self.ticks = []
        self.labels = []
        common = ingr_count.common_ingr(20)
        for x, i1 in enumerate(common):
            self.ticks.append(i1)
            ps = []
            for i2 in ingr_count.counter.keys():
                if i1 == i2:
                    continue
                ps.append((p_for_ingr[i1].get(i2, 0.0), i2))
            ps.sort(reverse=True)
            for p, i2 in ps[:5]:
                if p != 0.0:
                    self.result.append((x, p))
                    self.labels.append((x + 0.5, p, i2[:3]))

    def figure(self):
        x, y = zip(*self.result)
        plt.scatter(x, y)
        plt.xticks(ticks=range(len(self.ticks)), labels=self.ticks, rotation=90)
        for x, y, i in self.labels:
            plt.annotate(i, (x, y))
        plt.show()


def all_ingredients(inp: Input) -> set[Ingredient]:
    all_ingr = set()
    for _, pizza in inp.iter_pizzas():
        all_ingr |= set(pizza)
    return all_ingr


def all_pizzas(inp: Input) -> set[Pizza]:
    return set(pizza for _, pizza in inp.iter_pizzas())


def main():
    chk_inp = CheckFormat("pizzas")
    if chk_inp.any_error():
        chk_inp.report()
        return

    inp = Input("pizzas")
    ingr_count = IngredientCount(inp)
    common_ingr = ingr_count.common_ingr(ingr_common_limit)

    pizzagami = Pizzagami(inp, common_ingr)
    pizzagami.short_report()

    num_ingr = len(all_ingredients(inp))
    num_pizzas = len(all_pizzas(inp))
    # print("all ingredients:")
    # for ingr in sorted(all_ingredients(inp)):
    #    print("  ", ingr)
    print("number of ingredients: ", num_ingr)
    print("number of possible pizzas: 2**{} = {}".format(num_ingr, 2**num_ingr))
    print(
        "number of seen pizzas: {} ({:.0E} %)".format(
            num_pizzas, 100 * num_pizzas / (2**num_ingr)
        )
    )
    print("{} most common ingredients:".format(ingr_common_limit, common_ingr))
    counter = (
        ingr_count.counter_with_duplicates if with_duplicates else ingr_count.counter
    )
    for i, (pizza, amount) in enumerate(
        counter.most_common(ingr_common_limit), start=1
    ):
        print("  {:>2}. ({:>3}) {}".format(i, amount, pizza))

    is_pizzagami = [
        sorted(pizza) for pizza in all_pizzas(inp) if pizzagami.is_pizzagami(pizza)
    ]
    non_pizzagami = [
        sorted(pizza) for pizza in all_pizzas(inp) if not pizzagami.is_pizzagami(pizza)
    ]
    print(len(is_pizzagami), len(non_pizzagami), len(all_pizzas(inp)))

    # non_pizzagami_counts = sorted(
    #     (pizzagami.count(p, with_duplicates=True), p)
    #     for p in all_pizzas(inp)
    #     if not pizzagami.is_pizzagami(p)
    # )
    # xtick = [", ".join(s[:3] for s in p) for _, p in non_pizzagami_counts]
    # y = [c for c, _ in non_pizzagami_counts]
    # plt.bar(range(len(y)), y)
    # plt.xticks(ticks=range(len(y)), labels=xtick, rotation=90)
    # plt.show()

    # CountIngredientCommonPizzagami(pizzagami).report()
    # IngredientsAtOneStore(inp).report()
    # SameThings(inp).report()
    # ConditionalProbabilityOfIngredients(inp, min_pizzas_to_report=5).report()
    # FeasiblePizzas(inp).report()
    # StoreScatter(inp, pizzagami).figure()
    # IngredientScatter(ingr_count, ConditionalProbabilityOfIngredients(inp, min_pizzas_to_report=1)).figure()


main()
