from complex_calc.menus import MENU, find_path, iter_paths
from complex_calc.functions.registry import lookup_builtin
from complex_calc.core.session import Session


def test_normal_cdf_path():
    assert find_path("5", "5", "2").label == "Normal Cdf"      # confirmed by TI teacher notes
    assert find_path("5", "5", "3").label == "Inverse Normal"
    assert find_path("5", "5", "C").label == "Binomial Cdf"    # order from the official eGuide
    assert find_path("6", "7", "1").label == "z Test"
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
               "period": "", "d1": "3", "d2": "5", "k": "5", "s1": "2", "s2": "3", "m1": "10", "m2": "11",
               "n1": "20", "n2": "25", "sx1": "2", "sx2": "3", "l1": "{1,2,3,4,5}", "l2": "{2,3,4,5,7}",
               "l3": "{3,5,6}", "x1": "{1,2,3,4,5,6}", "mu0": "3", "obs": "{10,20,30}", "exp": "{20,20,20}",
               "m": "[10,20;30,40]", "xv": "2", "p0": "0.5", "freq1": "1", "freq2": "1"}
    for _, item in iter_paths():
        if item.wizard is None:
            continue
        for variant in item.wizard.variants.values():
            values = {f.key: (f.default or samples.get(f.key, "")) for f in variant.fields if f.enabled}
            for key in ("x", "n"):
                if key in values and key in samples and not values[key]:
                    values[key] = samples[key]
            if item.wizard.title.startswith(("Linear", "Quadratic", "Exponential", "Sinusoidal", "Median", "Cubic",
                                             "Quartic", "Power", "Logarithmic")):
                values["x"] = "{1,2,3,4,5,6}"
                values["y"] = "{2.1,3.9,6.2,8.1,9.7,12.2}"
            if item.wizard.title == "One-Variable Statistics":
                values["list"] = "{1,2,3,4,5}"
            if item.wizard.title in ("Two-Variable Statistics", "Linear Reg t Intervals", "Linear Reg t Test"):
                values["x"], values["y"] = "{1,2,3,4,5}", "{2,4,5,4,5}"
            if item.wizard.title.startswith(("1-Prop", "2-Prop")):
                values.update({"x": "60", "n": "100", "x1": "60", "n1": "100", "x2": "50", "n2": "100"})
            if item.wizard.title == "Multiple Linear Regression":
                values.update({"y": "{3,5,7,9,12}", "x1": "{1,2,3,4,5}", "x2": "{0,1,0,1,1}"})
            if item.wizard.title.startswith("Logistic"):
                values["x"], values["y"] = "{0,1,2,3,4,5,6}", "{1,2.7,6.6,13,18.7,21.8,23.3}"
            if item.wizard.title == "Finance Solver":
                values.update({"n": "60", "i": "10", "pv": "5000", "pmt": "0", "fv": "0", "solve": "Pmt"})
            command = variant.build(values)
            entry = session.run(command)
            assert not entry.error, f"{item.label}: {command} → {entry.text}"


def test_inserted_functions_exist():
    for _, item in iter_paths():
        if item.insert and item.insert.endswith("(") and not item.insert.startswith("►"):
            name = item.insert[:-1]
            assert lookup_builtin(name) is not None, name
