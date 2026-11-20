from complex_calc.menus import MENU, find_path, iter_paths
from complex_calc.functions.registry import lookup_builtin
from complex_calc.core.session import Session


def test_normal_cdf_path():
    assert find_path("6", "5", "2").label == "Normal Cdf"
    assert find_path("6", "6", "1").label == "z Interval"
    assert find_path("6", "6", "2").label == "t Interval"
    assert find_path("3", "1").label == "Solve"


def test_keys_are_unique_and_ordered():
    def check(items):
        keys = [i.key for i in items]
        assert len(keys) == len(set(keys))
        for item in items:
            check(item.children)
    check(MENU)


def test_wizards_build_valid_commands():
    session = Session()
    samples = {"x": "1", "mu": "0", "sigma": "1", "lo": "-1", "hi": "1", "area": "0.5", "df": "5",
               "n": "10", "p": "0.5", "c": "0.95", "lam": "2", "mean": "10", "sx": "2",
               "list": "{1,2,3,4,5}", "freq": "1", "y": "{2,4,6,8,10}", "save": "f1", "iter": "8",
               "period": ""}
    for _, item in iter_paths():
        if item.wizard is None:
            continue
        for variant in item.wizard.variants.values():
            values = {f.key: (f.default or samples.get(f.key, "")) for f in variant.fields if f.enabled}
            if item.wizard.title.startswith(("Linear", "Quadratic", "Exponential", "Sinusoidal")):
                values["x"] = "{1,2,3,4,5,6}"
                values["y"] = "{2.1,3.9,6.2,8.1,9.7,12.2}"
            if item.wizard.title == "One-Variable Statistics":
                values["list"] = "{1,2,3,4,5}"
            command = variant.build(values)
            entry = session.run(command)
            assert not entry.error, f"{item.label}: {command} → {entry.text}"


def test_inserted_functions_exist():
    for _, item in iter_paths():
        if item.insert and item.insert.endswith("("):
            name = item.insert[:-1]
            assert lookup_builtin(name) is not None, name
