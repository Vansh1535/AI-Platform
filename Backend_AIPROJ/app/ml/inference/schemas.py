from pydantic import BaseModel, Field, field_validator


class PredictRequest(BaseModel):
    """Request model for ML prediction."""
    features: list[float] = Field(
        ..., 
        description="Input features for prediction",
        min_length=1
    )
    
    @field_validator('features')
    @classmethod
    def validate_features(cls, v):
        """Ensure all features are valid numbers."""
        if not v:
            raise ValueError("Features list cannot be empty")
        return v


class PredictResponse(BaseModel):
    """Response model for ML prediction with telemetry."""
    prediction: int = Field(..., description="Predicted class")
    probabilities: list[float] = Field(..., description="Class probabilities")
    
    # Telemetry fields
    latency_ms_total: int = Field(..., description="Total processing time in milliseconds")
    model_name: str = Field(..., description="Name of the model used for prediction")
    cache_hit: bool = Field(default=False, description="Whether result came from cache")
    fallback_triggered: bool = Field(default=False, description="Whether fallback logic was used")
    degradation_level: str = Field(default="none", description="Degradation level: none, degraded, or fallback")
    graceful_message: str | None = Field(default=None, description="Message if degraded")

