# Описание

Wireguard Manager

# Установка
создаем пользователя

   sudo adduser wmuser

добавляем в группу root

   sudo usermod -aG root wmuser

1. генерируем ssh ключ 

   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"


2. клонируем репозитарий


    ``git clone https://github.com/vintello/wireguard_machine.git``

2. устанавливаем зависимости

    ``pip install -r requirements.txt``

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