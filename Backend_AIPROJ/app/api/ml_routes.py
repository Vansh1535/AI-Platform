from fastapi import APIRouter, HTTPException
from app.ml.inference.service import predict
from app.ml.inference.schemas import PredictRequest, PredictResponse
from app.core.logging import setup_logger
from datetime import datetime
import time

router = APIRouter()
logger = setup_logger("INFO")


@router.post("/predict", response_model=PredictResponse)
async def ml_predict(request: PredictRequest):
    """
    ML prediction endpoint with telemetry observability.
    
    Args:
        request: Input features for prediction
    
    Returns:
        Prediction result with class, probabilities, and telemetry fields
    
    Raises:
        HTTPException: 400 for validation errors, 503 for model not found, 500 for other errors
    """
    timestamp = datetime.now().isoformat()
    feature_count = len(request.features)
    start_time = time.time()
    
    logger.info(
        f"Prediction request received - Timestamp: {timestamp}, "
        f"Feature count: {feature_count}"
    )
    
    try:
        # Get prediction with timing
        prediction_result = predict(request.features)
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Build response with telemetry
        response = PredictResponse(
            prediction=prediction_result["prediction"],
            probabilities=prediction_result["probabilities"],
            latency_ms_total=latency_ms,
            model_name=prediction_result.get("model_name", "default_classifier"),
            cache_hit=prediction_result.get("cache_hit", False),
            fallback_triggered=prediction_result.get("fallback_triggered", False),
            degradation_level=prediction_result.get("degradation_level", "none"),
            graceful_message=prediction_result.get("graceful_message")
        )
        
        logger.info(
            f"Prediction completed successfully in {latency_ms}ms - "
            f"Class: {response.prediction}, Confidence: {max(response.probabilities):.4f}"
        )
        return response
        
    except FileNotFoundError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Model not found: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail=str(e)
        )
        
    except ValueError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail=str(e)
        )
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Unexpected error during prediction: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error during prediction: {str(e)}"
        )

