class OneOfstringarray:
    def __init__(self):
        pass

    @staticmethod
    def deserialize(data):
        if data:
            data = data if isinstance(data, list) else [data]
        return data
