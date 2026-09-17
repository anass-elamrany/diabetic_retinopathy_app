# Training experiments

These notebooks document exploratory experiments, not the provenance of the model currently used by the app. Their saved outputs and embedded images have been removed from the public copies. The original notebooks remain local under `notebooks/` and are ignored by Git.

- `CNN.ipynb` compares a four-block 512-pixel PyTorch CNN with EfficientNetB0 and ResNet50. The app's checkpoint uses a different three-block 256-pixel architecture.
- `Diabetic_Retinopathy_EfficientNetB0.ipynb` and `Diabetic_Retinopathy_ResNet50.ipynb` are TensorFlow experiments, not the source of the PyTorch `.pth` file.

The datasets are not included. The notebooks do not establish independent clinical validation. The original outputs reported weak performance for some disease stages, including 4% recall for class 2 in the 512-pixel CNN run and zero recall for class 3 in the smaller TensorFlow ensemble validations. These are exploratory results, not performance claims for the app's checkpoint. Before presenting any model as validated, document the dataset source and license, patient-level train/validation/test separation, exact preprocessing, class order, and per-class performance on an independent test set.
