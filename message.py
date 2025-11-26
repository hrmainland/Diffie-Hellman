class MessageObj:
    def __init__(self, text, from_name, to_name, to_url, stage, method="POST") -> None:
        self.text = text
        self.from_name = from_name
        self.to_name = to_name
        self.to_url = to_url
        self.stage = stage
        self.method = method
