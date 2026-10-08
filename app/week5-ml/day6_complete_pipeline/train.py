import csv
import torch
import torch.nn as nn
from model import BinaryClassifier
from data import get_loaders


def train(hidden=16, lr=0.05, epochs=20, log_path="metrics.csv"):
    net = BinaryClassifier(in_features=3, hidden=hidden)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.SGD(net.parameters(), lr=lr)
    train_loader, val_loader = get_loaders()

    best_acc = -1.0
    with open(log_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["epoch", "train_loss", "val_loss", "val_metric"])

        for epoch in range(1, epochs + 1):
            net.train()
            train_losses = []
            for X, y in train_loader:
                optimizer.zero_grad()
                predictions = net(X)
                loss = criterion(predictions, y)
                loss.backward()
                optimizer.step()
                train_losses.append(loss.item())

            net.eval()
            val_losses = []
            correct = 0
            total = 0
            with torch.no_grad():
                for X, y in val_loader:
                    predictions = net(X)
                    loss = criterion(predictions, y)
                    val_losses.append(loss.item())
                    probs = torch.sigmoid(predictions)
                    preds = (probs >= 0.5).float()
                    correct += (preds == y).sum().item()
                    total += y.size(0)

            avg_train = sum(train_losses) / len(train_losses)
            avg_val = sum(val_losses) / len(val_losses)
            acc = correct / total
            writer.writerow([epoch, f"{avg_train:.4f}", f"{avg_val:.4f}", f"{acc:.4f}"])
            print(f"epoch={epoch} train_loss={avg_train:.4f} val_loss={avg_val:.4f} val_acc={acc:.4f}")

            if acc > best_acc:
                best_acc = acc
                torch.save(net.state_dict(), "checkpoints/best.pt")
                print(f"  -> saved best checkpoint (acc={acc:.4f})")

    return best_acc


if __name__ == "__main__":
    train()
