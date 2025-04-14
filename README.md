# Описание

Wireguard Manager

# Установка
создаем пользователя

   sudo adduser wmuser

добавляем в группу root

   sudo usermod -aG root wmuser
   
   sudo adduser wmuser sudo


   su - wmuser

1. генерируем ssh ключ ????

   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"


2. клонируем репозитарий


    ``git clone https://github.com/vintello/wireguard_machine.git``

переходим в папку 

   cd wireguard_machine

создаем виртуальное окружение

   sudo apt install python3.12-venv

   python3 -m venv env

активируем виртуальное окружение 

   source env/bin/activate

2. устанавливаем зависимости

    ``pip install -r requirements.txt``

демонизируем приложение

   cp wireguad_machine.service wrg_machine.service
   nano wrg_machine.service 
   sudo cp wrg_machine.service  /etc/systemd/system/wrg_machine.service
   sudo systemctl enable wrg_machine
   sudo systemctl start wrg_machine

3. от имени администратора запускаем скрипты по установке и генерации пользователей
4. устанавливаем как сервис

Для этого необходимо единоразово выполнить следующую последовательность действий

    sudo cp wireguad_machine.service /lib/systemd/system/wireguad_machine.service
    sudo systemctl enable wireguad_machine
    sudo systemctl start wireguad_machine

проверяем что сервис успешно запущен 
    
    sudo systemctl status wireguad_machine

остановить-перезапустить сервис

    sudo systemctl stop wireguad_machine
    sudo systemctl restart wireguad_machine

5. добавляем айпи для доступа

# Заметки