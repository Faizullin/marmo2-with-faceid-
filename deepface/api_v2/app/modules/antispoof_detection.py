from deepface import DeepFace


def antispoof_detection():
    res = DeepFace.analyze(
        actions=("emotion",),
        anti_spoofing=True,
    )
