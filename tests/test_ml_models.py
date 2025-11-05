"""Tests for ML models."""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch

from features.ml_models import MLPredictor


class TestMLPredictor:
    """Test ML predictor."""
    
    def test_init(self, temp_dir):
        """Test ML predictor initialization."""
        predictor = MLPredictor(model_path=str(temp_dir / "models"), model_type="random_forest")
        
        assert predictor.model_path.exists()
        assert predictor.model_type == "random_forest"
        assert predictor.model is None
        assert not predictor.is_trained
    
    def test_init_gradient_boosting(self, temp_dir):
        """Test ML predictor with gradient boosting."""
        predictor = MLPredictor(model_path=str(temp_dir / "models"), model_type="gradient_boosting")
        
        assert predictor.model_type == "gradient_boosting"
    
    def test_init_invalid_type(self, temp_dir):
        """Test ML predictor with invalid model type."""
        with pytest.raises(ValueError):
            MLPredictor(model_path=str(temp_dir / "models"), model_type="invalid")
    
    def test_train_random_forest(self, temp_dir, sample_ohlc_data):
        """Test training Random Forest model."""
        from features.feature_engineering import FeatureEngineer
        
        predictor = MLPredictor(model_path=str(temp_dir / "models"), model_type="random_forest")
        
        # Prepare features and labels
        feature_engineer = FeatureEngineer()
        features = feature_engineer.prepare_features(sample_ohlc_data)
        labels = feature_engineer.create_labels(sample_ohlc_data)
        
        # Align indices
        common_idx = features.index.intersection(labels.index)
        features = features.loc[common_idx]
        labels = labels.loc[common_idx]
        
        # Train model
        metrics = predictor.train(features, labels, test_size=0.2)
        
        assert predictor.is_trained
        assert 'train_accuracy' in metrics
        assert 'test_accuracy' in metrics
        assert metrics['train_accuracy'] >= 0
        assert metrics['test_accuracy'] >= 0
    
    def test_train_gradient_boosting(self, temp_dir, sample_ohlc_data):
        """Test training Gradient Boosting model."""
        from features.feature_engineering import FeatureEngineer
        
        predictor = MLPredictor(model_path=str(temp_dir / "models"), model_type="gradient_boosting")
        
        # Prepare features and labels
        feature_engineer = FeatureEngineer()
        features = feature_engineer.prepare_features(sample_ohlc_data)
        labels = feature_engineer.create_labels(sample_ohlc_data)
        
        # Align indices
        common_idx = features.index.intersection(labels.index)
        features = features.loc[common_idx]
        labels = labels.loc[common_idx]
        
        # Train model
        metrics = predictor.train(features, labels, test_size=0.2)
        
        assert predictor.is_trained
        assert 'train_accuracy' in metrics
    
    def test_train_insufficient_data(self, temp_dir):
        """Test training with insufficient data."""
        predictor = MLPredictor(model_path=str(temp_dir / "models"))
        
        # Create minimal data
        features = pd.DataFrame({'feature1': [1, 2, 3]})
        labels = pd.Series([1, -1, 0])
        
        metrics = predictor.train(features, labels)
        
        assert 'error' in metrics
    
    def test_predict(self, temp_dir, sample_ohlc_data):
        """Test making predictions."""
        from features.feature_engineering import FeatureEngineer
        
        predictor = MLPredictor(model_path=str(temp_dir / "models"))
        
        # Prepare and train
        feature_engineer = FeatureEngineer()
        features = feature_engineer.prepare_features(sample_ohlc_data)
        labels = feature_engineer.create_labels(sample_ohlc_data)
        
        common_idx = features.index.intersection(labels.index)
        features_train = features.loc[common_idx]
        labels_train = labels.loc[common_idx]
        
        predictor.train(features_train, labels_train)
        
        # Make predictions
        predictions, probabilities = predictor.predict(features_train.tail(5))
        
        assert len(predictions) == 5
        assert len(probabilities) == 5
    
    def test_predict_untrained(self, temp_dir):
        """Test making predictions with untrained model."""
        predictor = MLPredictor(model_path=str(temp_dir / "models"))
        
        features = pd.DataFrame({'feature1': [1, 2, 3]})
        predictions, probabilities = predictor.predict(features)
        
        # Should return zeros
        assert len(predictions) == 3
        assert np.all(predictions == 0)
    
    def test_predict_signal(self, temp_dir, sample_ohlc_data):
        """Test predicting trading signal."""
        from features.feature_engineering import FeatureEngineer
        
        predictor = MLPredictor(model_path=str(temp_dir / "models"))
        
        # Prepare and train
        feature_engineer = FeatureEngineer()
        features = feature_engineer.prepare_features(sample_ohlc_data)
        labels = feature_engineer.create_labels(sample_ohlc_data)
        
        common_idx = features.index.intersection(labels.index)
        features_train = features.loc[common_idx]
        labels_train = labels.loc[common_idx]
        
        predictor.train(features_train, labels_train)
        
        # Predict signal
        signal = predictor.predict_signal(features_train.tail(1), threshold=0.6)
        
        assert signal in [-1, 0, 1]
    
    def test_save_and_load_model(self, temp_dir, sample_ohlc_data):
        """Test saving and loading model."""
        from features.feature_engineering import FeatureEngineer
        
        predictor = MLPredictor(model_path=str(temp_dir / "models"))
        
        # Prepare and train
        feature_engineer = FeatureEngineer()
        features = feature_engineer.prepare_features(sample_ohlc_data)
        labels = feature_engineer.create_labels(sample_ohlc_data)
        
        common_idx = features.index.intersection(labels.index)
        features_train = features.loc[common_idx]
        labels_train = labels.loc[common_idx]
        
        predictor.train(features_train, labels_train)
        
        # Save model
        predictor.save_model("test_model")
        
        # Create new predictor and load
        predictor2 = MLPredictor(model_path=str(temp_dir / "models"))
        loaded = predictor2.load_model("test_model")
        
        assert loaded
        assert predictor2.is_trained
        
        # Test predictions match
        predictions1, _ = predictor.predict(features_train.tail(5))
        predictions2, _ = predictor2.predict(features_train.tail(5))
        
        np.testing.assert_array_equal(predictions1, predictions2)
    
    def test_load_nonexistent_model(self, temp_dir):
        """Test loading non-existent model."""
        predictor = MLPredictor(model_path=str(temp_dir / "models"))
        loaded = predictor.load_model("nonexistent")
        
        assert not loaded
        assert not predictor.is_trained

