from sklearn.datasets import load_diabetes
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

data = load_diabetes()
X = data.data
y = data.target

X_train_val, X_test, y_train_val, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
X_train, X_val, y_train, y_val = train_test_split(
    X_train_val, y_train_val, test_size=0.25, random_state=42
)

model = LinearRegression()
model.fit(X_train, y_train)

train_predictions = model.predict(X_train)
val_predictions = model.predict(X_val)
print("Train MAE:", mean_absolute_error(y_train, train_predictions))
print("Validation MAE:", mean_absolute_error(y_val, val_predictions))

test_predictions = model.predict(X_test)
print("Test MAE:", mean_absolute_error(y_test, test_predictions))
