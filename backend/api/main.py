# api/main.py
from fastapi import FastAPI
from database import Base, engine
from routers.user import router as user_router

app = FastAPI(
    title="Backend API",
    description="API Backend avec FastAPI et PostgreSQL",
    version="1.0.0"
)

# Créer les tables dans la base de données
Base.metadata.create_all(bind=engine)

# Inclure les routers
app.include_router(user_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Backend API azdazda!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)