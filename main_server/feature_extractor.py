import os
import math
from collections import Counter

def calculate_entropy(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()

    if not data:
        return 0

    counter = Counter(data)
    total = len(data)

    entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in counter.values()
    )
    return entropy


def extract_features(file_path):
    file_size = os.path.getsize(file_path)
    entropy = calculate_entropy(file_path)

    extension = file_path.split('.')[-1].lower()
    ext_map = {
        "pdf": 1,
        "png": 2,
        "jpeg": 3,
        "jpg": 3,
        "txt": 4
    }

    ext_value = ext_map.get(extension, 0)

    return [file_size, entropy, ext_value]
