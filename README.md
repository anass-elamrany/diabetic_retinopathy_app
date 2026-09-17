# APTOS 2019 Blindness Detection

## About the project

Diabetic retinopathy (DR) is damage to the retina caused by diabetes. It can have no early symptoms, which makes regular eye examinations important. This project explores whether deep learning can help classify DR from a fundus photograph. It is an educational project, not a tool for clinical diagnosis. [Learn more about DR](https://www.nei.nih.gov/eye-health-information/eye-conditions-and-diseases/diabetic-retinopathy).

**Problem statement:** Build a machine learning model that can help sort retinal photographs into five DR severity stages.

![Project flow: retinal photograph, compatible model, and grade for review](docs/images/project-flow.svg)

## Dataset

The [APTOS 2019 Blindness Detection dataset](https://www.kaggle.com/c/aptos2019-blindness-detection) contains 3,662 labeled training photographs taken under different imaging conditions. A clinician assigned each image a grade from 0 to 4:

| Grade | Stage |
| --- | --- |
| 0 | No DR |
| 1 | Mild |
| 2 | Moderate |
| 3 | Severe |
| 4 | Proliferative DR |

There are 1,805 images labeled No DR and 1,857 labeled with a DR stage.

![APTOS training image counts: 1,805 No DR and 1,857 DR](docs/images/aptos-training-split.svg)

The notebooks in `research/notebooks/` explore CNN and transfer-learning approaches. The dataset photos are not included in this repository, and the notebooks do not document the training of the app's current model file.

## Django app

We built a web app where users can manage patients, schedule appointments, and upload retinal photographs for a predicted grade when a compatible model is installed. Patient and appointment features also work without the model.

**Built with:** Python, Django, HTML, CSS, JavaScript, and SQLite for local data. Optional image analysis uses PyTorch and OpenCV.

## Run locally

Use Python 3.12. In the project folder, run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/register/>, create an account, and sign in. You can add patients and appointments right away. To load fictional sample records, run `python manage.py seed_demo` and sign in with the `demo_clinic` account and password printed by the command.

**Optional image analysis:** Obtain a compatible `best_model.pth` from the project owner and place it at `app/model_weights/best_model.pth`. The file is not part of the Kaggle dataset or this Git repository. Install the extra packages below, restart the app, and use **Upload Image**. The model file must match `DRNet` in `app/utils.py`.

```bash
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install opencv-python-headless
```
