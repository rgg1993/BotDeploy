## CUESTIONES PRELIMINARES:

<ins>1. Se debe tener instalado ngrok<ins>
 
 El link de descarga está aquí: https://ngrok.com/
 Necesitamos ngrok ya que Teams requiere que la app cuente con un https para correrla

<ins>2. En el file /bots/teams_conversation_bot.py <ins>
  
  Los datos para correr el Jenkins Jobs fueron borrados, el usuario debe agregar los datos propios para correrlos (userName, userToken, jobName). 
  Además, el Jenkins debe habilitar la ejecución de Jobs a través de la API. 
   
   
 
## INSTRUCCIONES PARA AGREGAR EL BOT A TEAMS

<ins>1. Ir a la carpeta de GabotsGonnaWork, donde se encuentra el file app.py ejecutar los siguientes comandos: <ins>

```python3 -m pip install -r requirements.txt```

```python3 app.py```

Como resultado, la consola debera decir: 

```
peppers:~/GabotsGonnaWork$ python3 app.py
======== Running on http://localhost:3978 ========
```

<ins>2. Con la app corriendo en local host, ejecutar el ngrok. <ins>

 Dado que bot se corre en http://localhost:3978 , para obtener el https en la carpeta donde esté la app de ngrok ejecutamos el comando:
 
``` ./ngrok http -host-header=rewrite 3978 ```
 
El programa nos brinda una direccion https que deberemos guardar para agregar la app a Teams. Hay que recordar que esta dirección no es permanente, por lo que cada vez que dejemos de correr ngrok; deberemos actualizar el https en la apps de Teams como se demostrará mas adelante
 
 ![image](https://user-images.githubusercontent.com/70332427/113620600-ed5fb080-9630-11eb-9d43-c953c61e87cf.png)
 
<ins> 3. En Teams, buscamos AppsStudio, y seleccionamos "Import an Existing App "<ins>

![image](https://user-images.githubusercontent.com/70332427/113621520-15034880-9632-11eb-8c57-f7f628815ec5.png)

![image](https://user-images.githubusercontent.com/70332427/113621999-c5714c80-9632-11eb-8d78-6c7fb3a03da7.png)


<ins>4. Seleccionamos el manifest.zip en la carpeta de GabotsGonnaWork/teams_app_manifest y se nos debe abrir una pantalla donde configurar la app:<ins>

![image](https://user-images.githubusercontent.com/70332427/113622173-fcdff900-9632-11eb-9eb1-578c0320a8a4.png)

Ahi ingresamos el nombre que queremos, y en el menú a la izquierda debemos seleccionar 2.Capabilities, Bots.
En la sección de messaging endpoints agregamos el https obtenido con ngrok, y le agregamos /api/messages 

![image](https://user-images.githubusercontent.com/70332427/113622731-bccd4600-9633-11eb-91e6-0992ca9f53cd.png)


<ins>5. Luego, en el menú a la izquierda seleccionamos 3. Finish, Test and Distribute.<ins>

<ins>6. Seleccionamos "Install" y elegimos el teams en el cual querramos instalarlo<ins>

**Notas**: 

- Hay que recordar que cada vez que apaguemos el ngrok, debremos obtener una nueva https y actalizarla en Teams. Esto se hace en AppStudio-Bots Management, y ahi se selecciona el Bot en cuestión que se desea actualizar

- Se debe tener instalado bot builder 
```python3 -m pip install botbuilder-core```

- Los bots corren con Python3, por lo que python 2.7 o menores no funcionan. 
