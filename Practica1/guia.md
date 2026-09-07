# Guia para lo del contenedor

Para levantar el contenedor

    docker compose up -d

Para bajar el contenedor 

    docker compose down

o
    
    docker compose down -v




# Para ejecutar el scripp de python

por si vas a usar un entorno virtual de python ingresa el siguiente comando 

    python -m venv venv


Para activar el contenedor de python

    venv\Scripts\activate

Instalamos las dependencias

    pip install -r requirements.txt


Luego ya puedes ejecutar el script

si te da error verifica que no este nada coerriendo en el puerto que asignaste en el docker compose









# Para conectarde a la base de datos desde dbga con el navedor

Despues de ver levantadoo el contenedor ingresar al nevegador

    http://localhost:3000

ingresar una nueva coneccion con Microsof SQL Server

agregas el puerto 1433, el usuario  y la contraseña