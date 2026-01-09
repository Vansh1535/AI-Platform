"use client"

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { mlAPI } from "@/lib/api/endpoints";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import { Sparkles, TrendingUp, Zap } from "lucide-react";
import type { PredictResponse } from "@/lib/types/api";

const EXAMPLE_PRESETS = [
  { name: "Iris Setosa", features: [5.1, 3.5, 1.4, 0.2] },
  { name: "Iris Versicolor", features: [6.2, 2.9, 4.3, 1.3] },
  { name: "Iris Virginica", features: [7.2, 3.0, 5.8, 2.3] },
];

export default function MLPage() {
  const [features, setFeatures] = useState(["5.1", "3.5", "1.4", "0.2"]);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const { toast } = useToast();

  // Predict mutation
  const predictMutation = useMutation({
    mutationFn: (data: { features: number[] }) => mlAPI.predict(data.features),
    onSuccess: (data: PredictResponse) => {
      setResult(data);
      toast({
        title: "Prediction Complete",
        description: `Predicted: ${data.prediction}`,
        variant: "success",
      });
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.detail || "Failed to make prediction";
      toast({
        title: "Prediction Failed",
        description: errorMsg.includes("model") ? "Model not trained yet. Train a model first." : errorMsg,
        variant: "destructive",
      });
    },
  });

  const handlePredict = () => {
    const numericFeatures = features.map((f) => parseFloat(f));
    
    if (numericFeatures.some((f) => isNaN(f))) {
      toast({
        title: "Invalid Input",
        description: "Please enter valid numeric values for all features",
        variant: "destructive",
      });
      return;
    }

    if (numericFeatures.length !== 4) {
      toast({
        title: "Invalid Input",
        description: "Please provide exactly 4 feature values",
        variant: "destructive",
      });
      return;
    }

    setResult(null);
    predictMutation.mutate({ features: numericFeatures });
  };

  const loadPreset = (preset: { features: number[] }) => {
    setFeatures(preset.features.map((f) => f.toString()));
    setResult(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-neon-cyan to-neon-magenta bg-clip-text text-transparent">
          ML Predictions
        </h1>
        <p className="text-muted-foreground mt-2">
          Run predictions with trained machine learning models
        </p>
      </div>

      {/* Info Banner */}
      <Card className="border-yellow-500/50 bg-yellow-500/10">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <Zap className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-yellow-400 font-medium">Model Training Required</p>
              <p className="text-xs text-yellow-400/80 mt-1">
                If predictions fail, ensure the ML model is trained first using the backend training scripts.
                The default model uses the Iris dataset (4 features).
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Example Presets */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Example Presets</CardTitle>
          <CardDescription>Quick start with sample data</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_PRESETS.map((preset, idx) => (
              <Button
                key={idx}
                variant="outline"
                size="sm"
                onClick={() => loadPreset(preset)}
              >
                {preset.name}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Input Form */}
      <Card>
        <CardHeader>
          <CardTitle>Feature Input</CardTitle>
          <CardDescription>Enter feature values for prediction (Iris dataset)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Sepal Length (cm)</label>
              <Input
                type="number"
                step="0.1"
                value={features[0]}
                onChange={(e) => setFeatures([e.target.value, features[1], features[2], features[3]])}
                placeholder="e.g., 5.1"
              />
            </div>
            
            <div>
              <label className="text-sm font-medium mb-2 block">Sepal Width (cm)</label>
              <Input
                type="number"
                step="0.1"
                value={features[1]}
                onChange={(e) => setFeatures([features[0], e.target.value, features[2], features[3]])}
                placeholder="e.g., 3.5"
              />
            </div>
            
            <div>
              <label className="text-sm font-medium mb-2 block">Petal Length (cm)</label>
              <Input
                type="number"
                step="0.1"
                value={features[2]}
                onChange={(e) => setFeatures([features[0], features[1], e.target.value, features[3]])}
                placeholder="e.g., 1.4"
              />
            </div>
            
            <div>
              <label className="text-sm font-medium mb-2 block">Petal Width (cm)</label>
              <Input
                type="number"
                step="0.1"
                value={features[3]}
                onChange={(e) => setFeatures([features[0], features[1], features[2], e.target.value])}
                placeholder="e.g., 0.2"
              />
            </div>
          </div>

          <Button
            onClick={handlePredict}
            disabled={predictMutation.isPending}
            className="w-full"
          >
            {predictMutation.isPending ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                Predicting...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4 mr-2" />
                Predict
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Result Display */}
      {result && (
        <Card className="border-neon-green/50 animate-slide-in-right">
          <CardHeader>
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5 text-neon-green" />
              <CardTitle>Prediction Result</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Prediction */}
            <div className="text-center p-6 bg-gradient-to-br from-neon-cyan/20 to-neon-magenta/20 rounded-lg border border-neon-cyan/50">
              <p className="text-sm text-muted-foreground mb-2">Predicted Class</p>
              <p className="text-3xl font-bold text-neon-cyan">{result.prediction}</p>
            </div>

            {/* Probabilities */}
            {result.probabilities && (
              <div>
                <h4 className="text-sm font-semibold text-neon-cyan mb-3">Class Probabilities</h4>
                <div className="space-y-3">
                  {Object.entries(result.probabilities).map(([className, probability]: [string, any]) => (
                    <div key={className}>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm">{className}</span>
                        <span className="text-sm font-mono text-neon-cyan">
                          {(probability * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-2 bg-base-bg rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-neon-cyan to-neon-magenta transition-all duration-500"
                          style={{ width: `${probability * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Metadata */}
            {result.metadata && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-4 border-t border-neon-cyan/30">
                {result.metadata.model_name && (
                  <div>
                    <p className="text-xs text-muted-foreground">Model</p>
                    <p className="text-sm font-medium">{result.metadata.model_name}</p>
                  </div>
                )}
                
                {result.metadata.prediction_time !== undefined && (
                  <div>
                    <p className="text-xs text-muted-foreground">Latency</p>
                    <p className="text-sm font-medium text-neon-magenta">
                      {(result.metadata.prediction_time * 1000).toFixed(2)}ms
                    </p>
                  </div>
                )}
                
                {result.metadata.cache_hit !== undefined && (
                  <div>
                    <p className="text-xs text-muted-foreground">Cache</p>
                    <div className="flex items-center space-x-1">
                      <div className={`w-2 h-2 rounded-full ${result.metadata.cache_hit ? "bg-neon-green" : "bg-gray-500"}`}></div>
                      <p className="text-sm font-medium">
                        {result.metadata.cache_hit ? "Hit" : "Miss"}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Feature Importance (if available) */}
            {result.feature_importance && Object.keys(result.feature_importance).length > 0 && (
              <div className="pt-4 border-t border-neon-cyan/30">
                <h4 className="text-sm font-semibold text-neon-cyan mb-3 flex items-center">
                  <Zap className="h-4 w-4 mr-1" />
                  Feature Importance
                </h4>
                <div className="space-y-2">
                  {Object.entries(result.feature_importance)
                    .sort(([, a]: [string, any], [, b]: [string, any]) => b - a)
                    .map(([feature, importance]: [string, any]) => (
                      <div key={feature} className="flex items-center space-x-2">
                        <span className="text-sm w-32">{feature}</span>
                        <div className="flex-1 h-1.5 bg-base-bg rounded-full overflow-hidden">
                          <div
                            className="h-full bg-neon-purple"
                            style={{ width: `${importance * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-xs font-mono text-muted-foreground w-12 text-right">
                          {(importance * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
