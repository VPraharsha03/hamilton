import collections
import inspect
from typing import Any, Type

import numpy
import numpy as np
import pandas as pd
import pytest

from hamilton.data_quality import default_validators
from hamilton.data_quality.default_validators import resolve_default_validators, BaseDefaultValidator, AVAILABLE_DEFAULT_VALIDATORS
from tests.resources.dq_dummy_examples import SampleDataValidator1, SampleDataValidator2, SampleDataValidator3, DUMMY_VALIDATORS_FOR_TESTING


@pytest.mark.parametrize(
    'output_type, kwargs, importance, expected',
    [
        (int, {'equal_to': 1}, 'warn', [SampleDataValidator1(importance='warn', equal_to=1)]),
        (int, {'equal_to': 5}, 'fail', [SampleDataValidator1(importance='fail', equal_to=5)]),
        (pd.Series, {'dataset_length': 1}, 'warn', [SampleDataValidator2(importance='warn', dataset_length=1)]),
        (pd.Series, {'dataset_length': 5}, 'fail', [SampleDataValidator2(importance='fail', dataset_length=5)]),
        (
                pd.Series,
                {'dataset_length': 1, 'dtype': np.int64},
                'warn',
                [
                    SampleDataValidator2(importance='warn', dataset_length=1),
                    SampleDataValidator3(importance='warn', dtype=np.int64)
                ]
        ),
    ],
)
def test_resolve_default_validators(output_type, kwargs, importance, expected):
    resolved_validators = resolve_default_validators(
        output_type=output_type,
        importance=importance,
        available_validators=DUMMY_VALIDATORS_FOR_TESTING,
        **kwargs
    )
    assert resolved_validators == expected


@pytest.mark.parametrize(
    'output_type, kwargs, importance',
    [
        (str, {'dataset_length': 1}, 'warn'),
        (pd.Series, {'equal_to': 1}, 'warn')
    ],
)
def test_resolve_default_validators_error(output_type, kwargs, importance):
    with pytest.raises(ValueError):
        resolve_default_validators(
            output_type=output_type,
            importance=importance,
            available_validators=DUMMY_VALIDATORS_FOR_TESTING,
            **kwargs)


@pytest.mark.parametrize(
    'cls,param,data,should_pass',
    [
        (default_validators.DataInRangeValidatorPandas, (0, 1), pd.Series([0.1, 0.2, 0.3]), True),
        (default_validators.DataInRangeValidatorPandas, (0, 1), pd.Series([-30.0, 0.1, 0.2, 0.3, 100.0]), False),

        (default_validators.DataInRangeValidatorPrimitives, (0, 1), .5, True),
        (default_validators.DataInRangeValidatorPrimitives, (0, 1), 100.3, False),

        (default_validators.MaxFractionNansValidatorPandasSeries, .5, pd.Series([1.0, 2.0, 3.0, None]), True),
        (default_validators.MaxFractionNansValidatorPandasSeries, 0, pd.Series([1.0, 2.0, 3.0, None]), False),
        (default_validators.MaxFractionNansValidatorPandasSeries, .5, pd.Series([1.0, 2.0, None, None]), True),
        (default_validators.MaxFractionNansValidatorPandasSeries, .5, pd.Series([1.0, None, None, None]), False),
        (default_validators.MaxFractionNansValidatorPandasSeries, .5, pd.Series([None, None, None, None]), False),

        (default_validators.DataTypeValidatorPandas, numpy.dtype('int'), pd.Series([1, 2, 3]), True),
        (default_validators.DataTypeValidatorPandas, numpy.dtype('int'), pd.Series([1.0, 2.0, 3.0]), False),
        (default_validators.DataTypeValidatorPandas, numpy.dtype('object'), pd.Series(['hello', 'goodbye']), True),
        (default_validators.DataTypeValidatorPandas, numpy.dtype('object'), pd.Series([1, 2]), False),

        (default_validators.PandasMaxStandardDevValidator, 1.0, pd.Series([.1, .2, .3, .4]), True),
        (default_validators.PandasMaxStandardDevValidator, 0.01, pd.Series([.1, .2, .3, .4]), False),

        (default_validators.NansAllowedValidatorPandas, False, pd.Series([.1, None]), False),
        (default_validators.NansAllowedValidatorPandas, False, pd.Series([.1, .2]), True),
    ]
)
def test_default_data_validators(cls: Type[default_validators.BaseDefaultValidator], param: Any, data: Any, should_pass: bool):
    validator = cls(**{cls.arg(): param, 'importance': 'warn'})
    result = validator.validate(data)
    assert result.passes == should_pass


def test_to_ensure_all_validators_added_to_default_validator_list():
    def predicate(maybe_cls: Any) -> bool:
        if not inspect.isclass(maybe_cls):
            return False
        return issubclass(maybe_cls, BaseDefaultValidator) and maybe_cls != BaseDefaultValidator

    all_subclasses = inspect.getmembers(default_validators, predicate)
    missing_classes = [item for (_, item) in all_subclasses if item not in default_validators.AVAILABLE_DEFAULT_VALIDATORS]
    assert len(missing_classes) == 0


def test_that_all_validators_with_the_same_arg_have_the_same_name():
    kwarg_to_name_map = {}
    conflicting = collections.defaultdict(list)
    for validator in AVAILABLE_DEFAULT_VALIDATORS:
        print(validator.arg(), validator.name())
        if validator.arg() not in kwarg_to_name_map:
            kwarg_to_name_map[validator.arg()] = validator.name()
        if kwarg_to_name_map[validator.arg()] != validator.name():
            conflicting[validator.arg()] = validator.name()
    if len(conflicting) > 0:
        raise ValueError(f'The following args have multiple classes with different corresponding names. '
                         f'Validators with the same arg must all have the same name: {conflicting}')