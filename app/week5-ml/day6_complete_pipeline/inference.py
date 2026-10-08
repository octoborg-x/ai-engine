import torch
from model import BinaryClassifier


def infer(input_data):
    net = BinaryClassifier(in_features=3, hidden=16)
    net.load_state_dict(torch.load("checkpoints/best.pt", weights_only=True))
    net.eval()
    with torch.no_grad():
        tensor = torch.tensor(input_data, dtype=torch.float32)
        out = net(tensor)
        probs = torch.sigmoid(out)
        preds = (probs >= 0.5).float()
    result = []
    for i in range(len(input_data)):
        result.append({
            "input": input_data[i],
            "probability": round(probs[i].item(), 4),
            "prediction": int(preds[i].item()),
            "label": "positive" if preds[i].item() == 1 else "negative",
        })
    return result


if __name__ == "__main__":
    unseen = [[0.5, 0.5, -0.2], [-1.0, -0.8, 0.1]]
    print("Inference on unseen data:")
    for r in infer(unseen):
        print(r)
