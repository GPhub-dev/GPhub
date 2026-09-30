"""
Validate every library YAML against utils/libraries/base.yaml and the
canonical vocabularies hard-coded in layouts/partials/cell/*.html.

Usage (from gphub/):  python3 utils/validate/validate_libraries.py [dir]
Default dir: data/libraries. Exit code 1 when any ERROR is found.
"""
import collections
import glob
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
GPHUB = os.path.abspath(os.path.join(HERE, "..", ".."))
LIB_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(GPHUB, "data", "libraries")
BASE = os.path.join(GPHUB, "utils", "libraries", "base.yaml")

# Keep in sync with the {{if eq ...}} switches in layouts/partials/cell/*.html
CANON = {
    "Language": {"C", "C++", "GO", "Julia", "Matlab", "Octave", "Python", "R", "Rust"},
    "License": {"Apache-2.0", "BSD-3-Clause", "BSL-1.0", "FreeBSD", "GPL-2.0", "GPL-3.0", "LGPL", "MIT", "Custom"},
    "Installation": {"PyPI", "conda", "matlab", "Pkg.jl", "CRAN", "cargo"},
    "Framework": {"PyTorch", "TensorFlow", "NumPy", "SciPy", "JAX", "Numba", "NumPyro", "Optim.jl", "Distributions.jl"},
    "Complexity": {"O(N^3)", "O(N^2)", "O(N)", "O(NM^2)", "O(M^3)", r"\( \mathcal{O}(N + M \log M) \)"},
    "LengthScale": {"Isotropic", "Anisotropic"},
    "Metrics": {"RMSE", "MSE", "MAE", "R2", "LOOCV", "CV", "NLPD", "MAPE", "MedAE", "MSLL", "MSLE", "Validation Error"},
    "Support": {"blog", "chat", "contact form", "forum", "GitHub discussions", "mailing-list", "stackoverflow", "slack"},
    "Docs": {"docs", "py docs", "jl docs", "r docs", "mat docs", "user manuals", "examples", "py examples",
             "jl examples", "r examples", "API", "py API", "jl API", "r API", "tutorials",
             "jupyter notebooks", "colab notebooks", "talk"},
}
# select-value-color-<Tag> classes in static/style.css, plus the styleless "default"
TAGS = {"blue", "brown", "gray", "green", "orange", "pink", "purple", "red", "teal", "yellow", "uiBlue",
        "c", "cpp", "go", "julia", "matlab", "octave", "python", "r", "rust", "default"}
TYPED = ["Models", "Trend", "Correlation", "MixtureModels", "Likelihood", "EstimationMethods", "OptimizationMethods"]


def url_ok(url):
    return url is None or (isinstance(url, str) and url.startswith(("http://", "https://", "mailto:")))


def check(path, base_keys):
    errors, warnings = [], []
    err, warn = errors.append, warnings.append
    name = os.path.basename(path)[:-5]
    data = yaml.safe_load(open(path))
    if list(data.keys()) != base_keys:
        err(f"top-level keys differ from base.yaml: {list(data.keys())}")
        return errors, warnings
    if data["PackageID"] != name:
        err(f"PackageID {data['PackageID']!r} != filename {name!r}")
    lib = data["Library"][0]
    if not lib.get("URL"):
        warn("Library.URL is null")
    for ref in lib.get("Reference") or []:
        if not ref.get("Author") or not ref.get("URL"):
            warn("Reference is incomplete (Author or URL null)")
    for key in ["Language", "Installation", "Framework", "Complexity", "LengthScale", "Metrics"]:
        vals = data.get(key) or []
        for val in vals:
            if val is not None and val not in CANON[key]:
                warn(f"{key}: non-canonical value {val!r} (renders as grey default)")
        if len(vals) != len(set(map(str, vals))):
            err(f"{key}: duplicate values")
    for lic in data["License"]:
        if lic.get("Name") not in CANON["License"]:
            warn(f"License: non-canonical {lic.get('Name')!r}")
    for key in ["Support", "Docs"]:
        for entry in data.get(key) or []:
            if entry.get("Name") is None and entry.get("URL") is None:
                continue  # explicit "none"
            if entry.get("Name") not in CANON[key]:
                warn(f"{key}: non-canonical {entry.get('Name')!r}")
            if not url_ok(entry.get("URL")):
                err(f"{key}: bad URL {entry.get('URL')!r}")
    for dev in data.get("Developer") or []:
        if dev.get("Tag") is not None and dev["Tag"] not in TAGS:
            err(f"Developer: unknown Tag {dev['Tag']!r}")
        if not url_ok(dev.get("URL")):
            err(f"Developer: bad URL {dev.get('URL')!r}")
    repo, ver = data["Repository"][0], data["Version"][0]
    if repo.get("URL") and repo.get("Name") and "github.com" in repo["URL"]:
        if repo["URL"].rstrip("/").lower() != f"https://github.com/{repo['Name']}".lower():
            err(f"Repository: Name {repo['Name']!r} does not match URL {repo['URL']!r}")
    if not repo.get("Name"):
        warn("Repository is null (automatic version fetch skips this file)")
    if not ver.get("Name"):
        warn("Version is null")
    for key in TYPED:
        for block in data.get(key) or []:
            if block.get("URL") == "":
                err(f'{key}: URL is "" which hides the whole cell; use null')
            if not url_ok(block.get("URL")):
                err(f"{key}: bad URL {block.get('URL')!r}")
            types = block.get("Types") or []
            names = [t.get("Name") for t in types]
            for t in types:
                if (t.get("Name") is None) != (t.get("Tag") is None):
                    err(f"{key}: half-null entry {t}")
                if t.get("Tag") is not None and t["Tag"] not in TAGS:
                    err(f"{key}: unknown Tag {t['Tag']!r}")
            if any(n is None for n in names) and len(types) > 1:
                err(f"{key}: placeholder row mixed with real rows")
            dup = [n for n, cnt in collections.Counter(n for n in names if n).items() if cnt > 1]
            if dup:
                err(f"{key}: duplicate names {dup}")
            if key == "Likelihood":
                for sub in ["Nugget", "Noise"]:
                    for t in block.get(sub) or []:
                        if t.get("Tag") is not None and t["Tag"] not in TAGS:
                            err(f"{sub}: unknown Tag {t['Tag']!r}")
    has_mixture_models = any(t.get("Name") for b in data.get("MixtureModels") or [] for t in b.get("Types") or [])
    if data.get("Mixture") and not has_mixture_models:
        err("Mixture is true but MixtureModels is empty")
    if not data.get("Mixture") and has_mixture_models:
        err("Mixture is false but MixtureModels has entries")
    return errors, warnings


def main():
    base_keys = list(yaml.safe_load(open(BASE)).keys())
    n_err = n_warn = 0
    for path in sorted(glob.glob(os.path.join(LIB_DIR, "*.yaml")), key=str.lower):
        errors, warnings = check(path, base_keys)
        n_err += len(errors)
        n_warn += len(warnings)
        for msg in errors:
            print(f"ERROR   {os.path.basename(path)}: {msg}")
        for msg in warnings:
            print(f"WARNING {os.path.basename(path)}: {msg}")
    print(f"\n{n_err} errors, {n_warn} warnings")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
