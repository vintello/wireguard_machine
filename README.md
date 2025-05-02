# Описание

Wireguard Manager

# Установка
создаем пользователя

      sudo adduser wmuser

добавляем в группу root

      sudo usermod -aG root wmuser
      sudo adduser wmuser sudo
      su - wmuser


2. клонируем репозитарий


      git clone https://github.com/vintello/wireguard_machine.git

переходим в папку 

      cd wireguard_machine

создаем виртуальное окружение

      sudo apt install python3-venv
      python3 -m venv env

активируем виртуальное окружение 

      source env/bin/activate

устанавливаем зависимости 

      pip install -r requirements.txt

демонизируем приложение

      cp wireguad_machine.service wrg_machine.service
      nano wrg_machine.service -- если нужно что-то исправить 
      sudo cp wrg_machine.service  /etc/systemd/system/wrg_machine.service
      sudo systemctl enable wrg_machine
      sudo systemctl start wrg_machine

      sudo systemctl status wrg_machine

3. от имени администратора запускаем скрипты по установке 


      cd scripts
      sudo python3 wireguard_initial.py


# Заметки
   после добавления пользователей через вэб интерфейс перезагружать сервер не нужно, - добавляются в Wireguard динамически.
   после перезагрузки данные в Wireguard считываются из конфигурационных файлов и применяются

   export PYTHONPATH="${PYTHONPATH}:/home/vintello/Documents/wireguard_machine'

## если нет установленного > python 3.10

1 устанавливаем python 3.10

      sudo apt install software-properties-common -y
      sudo add-apt-repository ppa:deadsnakes/ppa
      sudo apt update
      sudo apt install python3.10

2. создаем виртуальное окружение и в дальнейшем используем его
   
      
