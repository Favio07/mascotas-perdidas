import torch
import torchvision.transforms as transforms
from torchvision.models import resnet50, ResNet50_Weights # <--- USAMOS RESNET50
from PIL import Image
import numpy as np

class MotorVision:
    def __init__(self):
        # 1. Cargar pesos (ResNet50 es mucho más potente para detalles finos)
        self.weights = ResNet50_Weights.DEFAULT
        self.full_model = resnet50(weights=self.weights)
        self.full_model.eval()
        
        # 2. Extractor de características (2048 dimensiones)
        self.feature_extractor = torch.nn.Sequential(*list(self.full_model.children())[:-1])
        self.feature_extractor.eval()
        
        self.preprocess = self.weights.transforms()

    def es_mascota(self, image_path_or_file):
        try:
            img = Image.open(image_path_or_file).convert('RGB')
            batch = self.preprocess(img).unsqueeze(0)
            
            with torch.no_grad():
                prediction = self.full_model(batch).squeeze(0).softmax(0)
                class_id = prediction.argmax().item()
                score = prediction[class_id].item()

            # Rangos ImageNet: 151-268 (Perros), 281-285 (Gatos)
            es_perro = 151 <= class_id <= 268
            es_gato = 281 <= class_id <= 285
            
            if es_perro: return True, f"Perro detectado ({score:.1%})"
            if es_gato: return True, f"Gato detectado ({score:.1%})"
            
            return False, f"Objeto desconocido (ID: {class_id})"
            
        except Exception as e:
            print(f"Error clf: {e}")
            return True, "Error Clasificación"

    def obtener_embedding(self, image_path_or_file):
        """
        TÉCNICA BIOMÉTRICA: Test Time Augmentation (TTA)
        Genera el vector de la imagen normal Y de la imagen volteada (espejo).
        El promedio de ambos crea una 'huella digital' resistente a la postura.
        """
        try:
            img = Image.open(image_path_or_file).convert('RGB')
            
            # 1. Imagen Normal
            img_tensor = self.preprocess(img).unsqueeze(0)
            
            # 2. Imagen Espejo (Flipped)
            img_flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
            img_tensor_flipped = self.preprocess(img_flipped).unsqueeze(0)
            
            with torch.no_grad():
                emb_original = self.feature_extractor(img_tensor).flatten()
                emb_flipped = self.feature_extractor(img_tensor_flipped).flatten()
            
            # 3. Fusión de Características (Promedio)
            # Esto crea un vector que representa al perro "desde ambos ángulos"
            embedding_final = (emb_original + emb_flipped) / 2.0
            
            # Convertir a float32 para DB
            return embedding_final.numpy().astype(np.float32)
            
        except Exception as e:
            print(f"Error embedding: {e}")
            return None

    def calcular_similitud(self, vector_a, vector_b):
        try:
            norm_a = np.linalg.norm(vector_a)
            norm_b = np.linalg.norm(vector_b)
            if norm_a == 0 or norm_b == 0: return 0.0
            return np.dot(vector_a, vector_b) / (norm_a * norm_b)
        except:
            return 0.0