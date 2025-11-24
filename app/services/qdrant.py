from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Any, Optional
from app.config import settings
import uuid

class QdrantService:
    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.url = settings.QDRANT_URL
    
    def connect(self):
        """Connect to Qdrant"""
        self.client = QdrantClient(url=self.url)
    
    def create_collection(self, collection_name: str, vector_size: int = 768):
        """Create a new collection"""
        if not self.client:
            self.connect()
        
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections"""
        if not self.client:
            self.connect()
        
        collections = self.client.get_collections()
        return [{"name": c.name} for c in collections.collections]
    
    def delete_collection(self, collection_name: str):
        """Delete a collection"""
        if not self.client:
            self.connect()
        
        self.client.delete_collection(collection_name=collection_name)
    
    def add_point(
        self,
        collection_name: str,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> str:
        """Add a point to collection"""
        if not self.client:
            self.connect()
        
        point_id = str(uuid.uuid4())
        
        self.client.upsert(
            collection_name=collection_name,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)]
        )
        
        return point_id
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        if not self.client:
            self.connect()
        
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )
        
        return [
            {
                "id": str(result.id),
                "score": result.score,
                "payload": result.payload
            }
            for result in results
        ]
    
    def check_connection(self) -> bool:
        """Check if Qdrant is available"""
        try:
            if not self.client:
                self.connect()
            self.client.get_collections()
            return True
        except:
            return False

qdrant_service = QdrantService()
