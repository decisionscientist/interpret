# Copyright (c) 2023 The InterpretML Contributors
# Distributed under the MIT software license

from itertools import count
from ..api.base import ExplainerMixin, ExplanationMixin
from ..utils import gen_name_from_class
from sklearn.metrics import roc_curve, auc
from sklearn.metrics import precision_recall_curve, average_precision_score

import numpy as np
from ..utils._binning import (
    preclean_X,
    determine_classes,
    unify_predict_fn,
    unify_data,
    clean_dimensions,
    typify_classification,
)


class PR(ExplainerMixin):
    """Produces precision-recall curves."""

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
        """Produce precision-recall curves.

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

        predict_fn, n_classes, classes = determine_classes(self.model, X, n_samples)
        if n_classes != 2:
            raise Exception("Only binary classification supported in the PR class")
        predict_fn = unify_predict_fn(predict_fn, X, 1)

        X, feature_names, feature_types = unify_data(
            X, n_samples, self.feature_names, self.feature_types, True, 0
        )

        y = typify_classification(y)
        if classes is None:
            # scikit-learn requires that the self.classes_ are sorted with np.unique, so rely on this
            classes, y = np.unique(y, return_inverse=True)
            if len(classes) != n_classes:
                raise ValueError("class number mismatch")
        else:
            invert_classes = dict(zip(classes, count(0)))
            y = np.array([invert_classes[el] for el in y], dtype=np.int64)

        scores = predict_fn(X)

        precision, recall, thresh = precision_recall_curve(y, scores)
        ap = average_precision_score(y, scores)

        abs_residuals = np.abs(y - scores)
        counts, values = np.histogram(abs_residuals, bins="doane")

        overall_dict = {
            "type": "perf_curve",
            "density": {"names": values, "scores": counts},
            "scores": scores,
            "x_values": recall,
            "y_values": precision,
            "threshold": thresh,
            "auc": ap,
        }
        internal_obj = {"overall": overall_dict, "specific": None}

        return PRExplanation(
            "perf",
            internal_obj,
            feature_names=feature_names,
            feature_types=feature_types,
            name=name,
        )


class ROC(ExplainerMixin):
    """Produces ROC curves."""

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
        """Produce ROC curves.

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

        predict_fn, n_classes, classes = determine_classes(self.model, X, n_samples)
        if n_classes != 2:
            raise Exception("Only binary classification supported in the ROC class")
        predict_fn = unify_predict_fn(predict_fn, X, 1)

        X, feature_names, feature_types = unify_data(
            X, n_samples, self.feature_names, self.feature_types, True, 0
        )

        y = typify_classification(y)
        if classes is None:
            # scikit-learn requires that the self.classes_ are sorted with np.unique, so rely on this
            classes, y = np.unique(y, return_inverse=True)
            if len(classes) != n_classes:
                raise ValueError("class number mismatch")
        else:
            invert_classes = dict(zip(classes, count(0)))
            y = np.array([invert_classes[el] for el in y], dtype=np.int64)

        scores = predict_fn(X)

        fpr, tpr, thresh = roc_curve(y, scores)
        roc_auc = auc(fpr, tpr)

        abs_residuals = np.abs(y - scores)
        counts, values = np.histogram(abs_residuals, bins="doane")

        overall_dict = {
            "type": "perf_curve",
            "density": {"names": values, "scores": counts},
            "scores": scores,
            "x_values": fpr,
            "y_values": tpr,
            "threshold": thresh,
            "auc": roc_auc,
        }
        internal_obj = {"overall": overall_dict, "specific": None}

        return ROCExplanation(
            "perf",
            internal_obj,
            feature_names=feature_names,
            feature_types=feature_types,
            name=name,
        )


class ROCExplanation(ExplanationMixin):
    """Explanation object specific to ROC explainer."""

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
        from ..visual.plot import plot_performance_curve

        data_dict = self.data(key)
        if data_dict is None:
            return None

        return plot_performance_curve(
            data_dict,
            xtitle="FPR",
            ytitle="TPR",
            baseline=True,
            title="ROC Curve: " + self.name,
            auc_prefix="AUC",
        )


class PRExplanation(ExplanationMixin):
    """Explanation object specific to PR explainer."""

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
        from ..visual.plot import plot_performance_curve

        data_dict = self.data(key)
        if data_dict is None:
            return None

        return plot_performance_curve(
            data_dict,
            xtitle="Recall",
            ytitle="Precision",
            baseline=False,
            title="PR Curve: " + self.name,
            auc_prefix="Average Precision",
        )
