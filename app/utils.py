from PIL import Image
import os

class DRModel:
    def __init__(self):
        self.available = False
        self.unavailable_reason = ""
        self.model = self._load_model()
        if self.available:
            from torchvision import transforms

            self.transform = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            ])
        else:
            self.transform = None
        
    def _load_model(self):
        try:
            import torch
            import torch.nn as nn
        except ImportError as exc:
            self.unavailable_reason = f"ML dependencies are not installed: {exc}"
            return None

        model_path = os.path.join(os.path.dirname(__file__), 'model_weights', 'best_model.pth')
        if not os.path.exists(model_path):
            self.unavailable_reason = f"Model weights not found at {model_path}"
            return None

        # Define your model architecture (must match training)
        class DRNet(nn.Module):
            def __init__(self):
                super(DRNet, self).__init__()
                self.features = nn.Sequential(
                    nn.Conv2d(3, 32, kernel_size=3, padding=1),
                    nn.BatchNorm2d(32),
                    nn.ReLU(),
                    nn.MaxPool2d(2, 2),
                    nn.Conv2d(32, 64, kernel_size=3, padding=1),
                    nn.BatchNorm2d(64),
                    nn.ReLU(),
                    nn.MaxPool2d(2, 2),
                    nn.Conv2d(64, 128, kernel_size=3, padding=1),
                    nn.BatchNorm2d(128),
                    nn.ReLU(),
                    nn.MaxPool2d(2, 2),
                )
                self.classifier = nn.Sequential(
                    nn.Linear(128 * (256//8) * (256//8), 256),
                    nn.ReLU(),
                    nn.Dropout(0.5),
                    nn.Linear(256, 5)
                )
                
            def forward(self, x):
                x = self.features(x)
                x = x.view(x.size(0), -1)
                x = self.classifier(x)
                return x

        model = DRNet()
        model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu'), weights_only=True))
        model.eval()
        self.available = True
        return model

    def preprocess(self, image_path):
        """Apply the same preprocessing as during training"""
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Circle crop
        height, width = img.shape[:2]
        mask = np.zeros((height, width), np.uint8)
        cv2.circle(mask, (width//2, height//2), int(min(width,height)/2), 255, -1)
        img = cv2.bitwise_and(img, img, mask=mask)
        
        # CLAHE for contrast
        lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        lab = cv2.merge((l,a,b))
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        
        # Sharpening
        img = cv2.addWeighted(img, 4, cv2.GaussianBlur(img, (0,0), 10), -4, 128)
        img = cv2.resize(img, (256, 256))
        
        return Image.fromarray(img)

    def predict(self, image_path):
        """Make prediction on a single image"""
        if not self.available:
            raise RuntimeError(self.unavailable_reason)

        import torch

        img = self.preprocess(image_path)
        img_tensor = self.transform(img).unsqueeze(0)
        
        with torch.no_grad():
            outputs = self.model(img_tensor)
            probs = torch.nn.functional.softmax(outputs, dim=1)
        
        return {
            'class': int(torch.argmax(probs)),
            'confidence': float(torch.max(probs)),
            'probabilities': probs.tolist()[0]
        }
