import torch
from torch.utils.data import Dataset, DataLoader, random_split


class TabularDataset(Dataset):
    def __init__(self, n=200):
        torch.manual_seed(42)
        self.X = torch.randn(n, 3)
        self.y = (self.X[:, 0] + self.X[:, 1] > 0).float().unsqueeze(1)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


def get_loaders(batch_size=16, n=200):
    dataset = TabularDataset(n=n)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_ds, val_ds = random_split(
        dataset, [train_size, val_size], generator=torch.Generator().manual_seed(42)
    )
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)
    return train_loader, val_loader
