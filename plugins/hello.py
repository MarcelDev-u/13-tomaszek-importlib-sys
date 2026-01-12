def main(argv):
    name = "world"
    if "--name" in argv:
        i = argv.index("--name")
        if i + 1 < len(argv):
            name = argv[i + 1]
    print(f"hello, {name}")
    return 0
