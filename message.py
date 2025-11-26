class MessageObj:
    def __init__(
        self, body, from_name, to_name, to_url, stage, signature=None, method="POST"
    ) -> None:
        self.body = body
        self.from_name = from_name
        self.to_name = to_name
        self.to_url = to_url
        self.stage = stage
        self.signature = signature
        self.method = method
