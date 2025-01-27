# Copyright (c) 2023 The InterpretML Contributors
# Distributed under the MIT software license

from ..api.base import ExplainerMixin, ExplanationMixin
from ..utils import gen_name_from_class

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np

from ..utils._binning import (
    preclean_X,
    determine_classes,
    unify_predict_fn,
    unify_data,
    clean_dimensions,
)


class RegressionPerf(ExplainerMixin):
    """Produces variety of regression metrics (including RMSE, R^2, etc)."""

    available_explanations = ["perf"]
    explainer_type = "perf"

    def __init__(self, model, feature_names=None, feature_types=None):
        """Initializes class.

        Args:
            model: model or prediction function of model (predict_proba for classification or predict for regression)
            feature_names: List of feature names.
            feature_types: List of feature types.
        """
        self.model = model
        self.feature_names = feature_names
        self.feature_types = feature_types

    def explain_perf(self, X, y, name=None):
        """Produces regression metrics.

        Args:
            X: Numpy array for X to compare predict function against.
            y: Numpy vector for y to compare predict function against.
            name: User-defined explanation name.

        Returns:
            An explanation object.
        """
        if name is None:
            name = gen_name_from_class(self)

        y = clean_dimensions(y, "y")
        if y.ndim != 1:
            raise ValueError("y must be 1 dimensional")

        X, n_samples = preclean_X(X, self.feature_names, self.feature_types, len(y))

        predict_fn, n_classes, _ = determine_classes(self.model, X, n_samples)
        if 0 <= n_classes:
            raise Exception("Classification not supported by the RegressionPerf class")
        predict_fn = unify_predict_fn(predict_fn, X, -1)

        X, feature_names, feature_types = unify_data(
            X, n_samples, self.feature_names, self.feature_types, True, 0
        )

        y = y.astype(np.float64, copy=False)

        scores = predict_fn(X)

        mse = mean_squared_error(y, scores)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y, scores)
        r2 = r2_score(y, scores)
        residuals = y - scores

        # abs_residuals = np.abs(y - scores)
        counts, values = np.histogram(residuals, bins="doane")

        overall_dict = {
            "type": "perf_curve",
            "density": {"names": values, "scores": counts},
            "scores": scores,
            "mse": mse,
            "rmse": rmse,
            "mae": mae,
            "r2": r2,
            "residuals": residuals,
        }
        internal_obj = {"overall": overall_dict, "specific": None}

        return RegressionExplanation(
            "perf",
            internal_obj,
            feature_names=feature_names,
            feature_types=feature_types,
            name=name,
        )


class RegressionExplanation(ExplanationMixin):
    """Produces explanation specific to regression metrics."""

    explanation_type = None

    def __init__(
        self,
        explanation_type,
        internal_obj,
        feature_names=None,
        feature_types=None,
        name=None,
        selector=None,
    ):
        """Initializes class.

        Args:
            explanation_type:  Type of explanation.
            internal_obj: A jsonable object that backs the explanation.
            feature_names: List of feature names.
            feature_types: List of feature types.
            name: User-defined name of explanation.
            selector: A dataframe whose indices correspond to explanation entries.
        """
        self.explanation_type = explanation_type
        self._internal_obj = internal_obj
        self.feature_names = feature_names
        self.feature_types = feature_types
        self.name = name
        self.selector = selector

    def data(self, key=None):
        """Provides specific explanation data.

        Args:
            key: A number/string that references a specific data item.

        Returns:
            A serializable dictionary.
        """
        if key is None:
            return self._internal_obj["overall"]
        return None

    def visualize(self, key=None):
        """Provides interactive visualizations.

        Args:
            key: Either a scalar or list
                that indexes the internal object for sub-plotting.
                If an overall visualization is requested, pass None.

        Returns:
            A Plotly figure.
        """
        from ..visual.plot import plot_density

        data_dict = self.data(key)
        if data_dict is None:
            return None

        rmse = data_dict["rmse"]
        r2 = data_dict["r2"]

        title = "{0} <br> RMSE = {1:.2f}" + " | R<sup>2</sup> = {2:.2f}"
        title = title.format(self.name, rmse, r2)
        density_fig = plot_density(
            data_dict["density"], title=title, xtitle="Residuals", ytitle="Density"
        )
        return density_fig
