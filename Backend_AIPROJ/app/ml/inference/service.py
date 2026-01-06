import os
from pathlib import Path
import joblib
import numpy as np
from typing import Optional
from app.core.logging import setup_logger

# Initialize logger
logger = setup_logger("INFO")

# Global variable to cache the loaded model
_model: Optional[object] = None


def get_model_path() -> Path:
    """Get the path to the saved model file."""
    return Path(__file__).parent.parent.parent.parent / "artifacts" / "model.pkl"


def load_model():
    """
    Load the trained model from disk.
    
    Returns:
        The loaded model
    
    Raises:
        FileNotFoundError: If the model file doesn't exist
    """
    global _model
    
    if _model is None:
        model_path = get_model_path()
        
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found at {model_path}. "
                "Please run the training script first: python -m src.ml.training.train"
            )
        
        _model = joblib.load(model_path)
        logger.info("Model loaded successfully")
    
    return _model


def get_expected_feature_count() -> int:
    """
    Get the expected number of features for the model.
    
    Returns:
        Expected number of input features
    """
    model = load_model()
    # For scikit-learn models, n_features_in_ contains the expected feature count
    return model.n_features_in_


def predict(input_features: list) -> dict:
    """
    Run inference using the trained model.
    
    Args:
        input_features: List of feature values for prediction
    
    Returns:
        Prediction result with class and probabilities
    
    Raises:
        FileNotFoundError: If the model file doesn't exist
        ValueError: If input features are invalid
    """
    try:
        # Load the model
        model = load_model()
        
        # Validate feature count
        expected_features = get_expected_feature_count()
        if len(input_features) != expected_features:
            error_msg = (
                f"Invalid feature count. Expected {expected_features} features, "
                f"got {len(input_features)}"
            )
            logger.error(f"Prediction validation failed: {error_msg}")
            raise ValueError(error_msg)
        
        # Reshape input for single prediction
        features = np.array(input_features).reshape(1, -1)
        
        # Get prediction and probabilities
        prediction = model.predict(features)[0]
        probabilities = model.predict_proba(features)[0].tolist()
        
        result = {
            "prediction": int(prediction),
            "probabilities": probabilities
        }
        
        logger.info(
            f"Prediction successful - Features: {len(input_features)}, "
            f"Result: class {prediction}"
        )
        
        return result
        
    except FileNotFoundError:
        logger.error("Model file not found")
        raise
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Prediction failed with unexpected error: {str(e)}")
        raise RuntimeError(f"Prediction failed: {str(e)}")
