"""The restored multi-view ``TargetTrainingOrder`` / ``pi_train`` owner.

D1 ``docs/methods/mlff_target_training_order_scientific_method.md``, D2
``docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`` and
D3 ``docs/arch_manuals/mlff_training_data/45_target_training_order.md`` govern
this package.  ``prepare`` reaches it only through
:func:`mdstats.training_data.target_order.preparation.prepare_target_training_order`;
downstream commands consume the resulting P2 projection.  The package imports
nothing eagerly so the compact P2 records never load selector machinery.
"""
