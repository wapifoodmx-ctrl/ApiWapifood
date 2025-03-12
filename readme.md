#Dos formas de ejecutar 
  1- uvicorn main:app
  2- agregar las lineas de codigo 

if __name__ == "__main__":
    uvicorn.run("main:app", port = 8000)

