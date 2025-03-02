from typing import Dict, List


def _merge(name, d, override_keys):
    override = d.pop("override", None)
    if override is not None:
        if not isinstance(override, dict):
            raise ValueError(
                f"{name}.override: got {type(override)}, must be a dictionary"
            )
        for k in override_keys:
            v = override.get(k, None)
            if v is not None:
                if not isinstance(v, dict):
                    raise ValueError(
                        f"{name}.override.{k}: got {type(v)}, must be a dictionary"
                    )
                d.update(v)

    for k, v in d.items():
        if isinstance(v, dict):
            _merge(f"{name}.{k}", v, override_keys)
        elif isinstance(v, list):
            for i in v:
                if isinstance(i, dict):
                    _merge(f"{name}.{k}[{i}]", i, override_keys)


def apply_overrides(d: Dict, override_keys: List[str]):
    """
    The idea is that any dictionary key can contain a key
    called 'override', which will be processed as follows:

    - override contents must be a dictionary
      - key is a potential 'override key'
      - value must be a dictionary
    - If a key matches an override key, then the contained
      dictionary will be shallow updated with the contents
      of the dictionary
    - This will recurse all structures and implement overrides
      wherever dictionaries are found

    Currently, if a list is overridden, the entire list is replaced. It may
    make sense to provide
    """
    _merge("", d, override_keys)


def _main():
    import argparse
    import tomli
    import tomli_w

    parser = argparse.ArgumentParser()
    parser.add_argument("fname")
    parser.add_argument("key")
    args = parser.parse_args()

    with open(args.fname, "rb") as fp:
        d = tomli.load(fp)

    apply_overrides(d, [args.key])
    print(tomli_w.dumps(d))


if __name__ == "__main__":
    _main()
