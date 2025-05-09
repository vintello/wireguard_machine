# Описание

Wireguard Manager

# Установка

устанавливаем системные пакеты

      sudo apt update
      sudo apt-get install python3-virtualenv
      sudo apt install build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev

проверяем версию python
      
      python3 --version

для работы приложения нужна версия 3.10+

если версия ниже производим добавление необходимой версии

      sudo apt install software-properties-common -y
      sudo add-apt-repository ppa:deadsnakes/ppa
      sudo apt update
      sudo apt install python3.10
      

проверяем что python установился корректно

      python3.10 --version

если выдало что команда не найдена то устанавливаем из исходников

      sudo apt install build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev
      wget https://www.python.org/ftp/python/3.10.0/Python-3.10.0.tgz
      tar -xf Python-3.10.*.tgz
      cd Python-3.10.*/
      ./configure --enable-optimizations
      make -j 4
      sudo make altinstall

!!!! если устанавливали версию python 3.10 то на шаге "создаем виртуальное окружение" python3 заменяем на python3.10 !!!!

доустанавливаем пакет

        sudo apt install python3.10-venv

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

      python3 -m venv env

активируем виртуальное окружение 

      source env/bin/activate

устанавливаем зависимости 

      pip install -r requirements.txt

демонизируем приложение

      cp wireguad_machine.service wrg_machine.service
      nano wrg_machine.service -- если нужно что-то исправить то делаем здесь
      sudo cp wrg_machine.service  /etc/systemd/system/wrg_machine.service
      sudo systemctl enable wrg_machine
      sudo systemctl start wrg_machine

      sudo systemctl status wrg_machine

3. от имени администратора запускаем скрипты по установке 
      
      cd scripts

      sudo python3 wireguard_initial.py

далее переходим в вэбинтрефейс и пользуемся 


# Заметки
   после добавления пользователей через вэб интерфейс перезагружать сервер не нужно, - добавляются в Wireguard динамически.
   после перезагрузки данные в Wireguard считываются из конфигурационных файлов и применяются

   export PYTHONPATH="${PYTHONPATH}:/home/vintello/Documents/wireguard_machine'


   
      
