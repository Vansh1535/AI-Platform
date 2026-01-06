import os
from pathlib import Path
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib


def train_model():
    """
    Train a RandomForest classifier on the Iris dataset and save it.
    """
    # Load the iris dataset
    print("Loading iris dataset...")
    iris = load_iris()
    X, y = iris.data, iris.target
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train the model
    print("Training RandomForest classifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate the model
    accuracy = model.score(X_test, y_test)
    print(f"Model accuracy on test set: {accuracy:.2f}")
    
    # Create artifacts directory if it doesn't exist
    artifacts_dir = Path(__file__).parent.parent.parent.parent / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    
    # Save the model
    model_path = artifacts_dir / "model.pkl"
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")
    
    return model_path


if __name__ == "__main__":
    train_model()
