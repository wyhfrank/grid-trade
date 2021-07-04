import sys

print(sys.argv)

if len(sys.argv) > 1:
    config_file = sys.argv[1]
    print(config_file)