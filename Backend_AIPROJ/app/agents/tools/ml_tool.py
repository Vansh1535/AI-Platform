"""
ML tool for agent workflows.
Provides machine learning prediction capabilities.
"""

import time
from typing import Dict, Any, List, Tuple
from app.core.logging import setup_logger
from app.core.cache import get_ml_cache
from app.core.config import settings
from app.ml.inference.service import predict
from app.ml.inference.schemas import PredictRequest

logger = setup_logger()


def predict_ml(features: List[float]) -> Tuple[str, Dict]:
    """
    Make a prediction using the ML model.
    
    Args:
        features: List of 4 numerical features for iris classification:
                  [sepal_length, sepal_width, petal_length, petal_width]
        
    Returns:
        Tuple of (prediction_str, telemetry_dict):
            prediction_str: The prediction result with species and confidence
            telemetry_dict: Execution metadata (latency, cache hit, etc.)
        
    Example:
        result, meta = predict_ml([5.1, 3.5, 1.4, 0.2])
    """
    start_time = time.time()
    
    # Initialize telemetry
    telemetry = {
        "latency_ms_ml": 0,
        "cache_hit": False,
        "error_class": None,
        "mode": "ml_prediction"
    }
    
    try:
        # Validate features
        if len(features) != 4:
            telemetry["error_class"] = "INVALID_FEATURES"
            telemetry["latency_ms_ml"] = int((time.time() - start_time) * 1000)
            error_msg = f"Error: Expected 4 features, got {len(features)}. Required: [sepal_length, sepal_width, petal_length, petal_width]"
            return error_msg, telemetry
        
        # Get ML cache
        ml_cache = get_ml_cache()
        
        # Generate cache key from features
        cache_key = f"ml:{','.join(str(f) for f in features)}"
        
        # Check cache if enabled
        if settings.CACHE_ENABLED:
            cached_result = ml_cache.get(cache_key)
            if cached_result:
                logger.info(f"cache_status=hit features={features}")
                telemetry["cache_hit"] = True
                telemetry["latency_ms_ml"] = int((time.time() - start_time) * 1000)
                return cached_result, telemetry
            
            logger.info(f"cache_status=miss")
        
        # Call prediction service directly with list (not PredictRequest)
        result = predict(features)
        logger.info(f"ML tool made prediction for features: {features}")
        
        # Format the response
        prediction = result.get("prediction", "unknown")
        probabilities = result.get("probabilities", [])
        
        # Calculate confidence (max probability)
        confidence = max(probabilities) if probabilities else 0.0
        
        # Map prediction to species name
        species_map = {0: "Setosa", 1: "Versicolor", 2: "Virginica"}
        species = species_map.get(prediction, f"Class {prediction}")
        
        prediction_str = f"Prediction: {species} (confidence: {confidence:.2%})"
        
        # Cache the result if enabled
        if settings.CACHE_ENABLED:
            ml_cache.set(cache_key, prediction_str)
            logger.info(f"cache_operation=set species={species}")
        
        telemetry["latency_ms_ml"] = int((time.time() - start_time) * 1000)
        return prediction_str, telemetry
        
    except ValueError as e:
        logger.error(f"ML tool validation error: {str(e)}")
        telemetry["error_class"] = "VALIDATION_ERROR"
        telemetry["latency_ms_ml"] = int((time.time() - start_time) * 1000)
        return f"Validation error: {str(e)}", telemetry
    except Exception as e:
        logger.error(f"ML tool error: {str(e)}")
        telemetry["error_class"] = "ML_SERVICE_ERROR"
        telemetry["latency_ms_ml"] = int((time.time() - start_time) * 1000)
        return f"Error making prediction: {str(e)}", telemetry


def get_ml_tool_definition() -> Dict[str, Any]:
    """
    Get the tool definition for Google AgentKit.
    
    Returns:
        dict: Tool definition with name, description, and parameters
    """
    return {
        "name": "predict_ml",
        "description": (
            "Classify iris flowers using machine learning based on 4 measurements. "
            "ALWAYS use this tool for: iris classification, flower predictions, "
            "or when given 4 numerical measurements (sepal length, sepal width, petal length, petal width). "
            "Extract the 4 numbers from user input and pass them as an array to this tool. "
            "NOTE: Named parameters (sepal_length, sepal_width, petal_length, petal_width) will be automatically converted to array format."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "features": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": (
                        "List of 4 numerical features: "
                        "[sepal_length, sepal_width, petal_length, petal_width]. "
                        "Example: [5.1, 3.5, 1.4, 0.2]"
                    ),
                    "minItems": 4,
                    "maxItems": 4
                }
            },
            "required": ["features"]
        }
    }
