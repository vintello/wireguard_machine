$(document).ready(function() {

var table = new DataTable('#example', {
    info: true,
    order: [[1, 'desc']],
    ajax: {
        url: '/whitelist',
        type: 'GET'
    },
    columns: [
        { data: 'id' },
        { data: 'ip_addr' },
    ],
    select: {
        blurable: true,
        style: 'os'
    },
    processing: true,
    layout: {
            top1Start: {
                buttons: [
                    {
                            text: '<span class="fa-solid fa-user"></span> Добавить ',
                            className: "btn btn-success delete",
                            enabled: true,
                            action: function(e, dt, node, config) {

                                    $.confirm({
                                        title: 'Добавление пользователя',
                                        type: 'green',
                                        content: '' +
                                        '<form action="" class="formName">' +
                                        '<div class="form-group">' +
                                        '<label>Введите IP адрес для разрешения доступа</label>' +

                                        '<input type="text" placeholder="xxx.xxx.xxx.xxx" class="name form-control ipv4" pattern="^([0-9]{1,3}\.){3}[0-9]{1,3}$" required />' +
                                        '</div>' +
                                        '</form>',
                                        onOpen: function(){
                                            $('.ipv4').mask('0ZZ.0ZZ.0ZZ.0ZZ', {translation: {'Z': {pattern: /[0-9]/, optional: true}}});
                                        },
                                        buttons: {
                                            formSubmit: {
                                                text: 'Добавить',
                                                btnClass: 'btn-blue',
                                                action: function () {
                                                    var ip4 = this.$content.find('.name').val();
                                                    if(!ip4.match("^([0-9]{1,3}\.){3}[0-9]{1,3}$")){
                                                        $.alert('не корректный ввод');
                                                        return false;
                                                    }

                                                    $.ajax( {url: '/whitelist',
                                                        type: 'POST',
                                                        processData: false,
                                                        contentType: false,
                                                        contentType: "application/json",
                                                        dataType: "json",
                                                        data:JSON.stringify([{"ip_addr": ip4}]),
                                                        success: function(data_resp) {
                                                            table.ajax.reload();
                                                        },
                                                        error: function(response) {
                                                            console.log(response);
                                                        }
                                                    });

                                                }
                                            },
                                            cancel: {
                                                text: 'Отменить',
                                                btnClass: 'btn-secondary',
                                                //close
                                            },
                                        },
                                        onContentReady: function () {
                                            // bind to events
                                            var jc = this;
                                            this.$content.find('form').on('submit', function (e) {
                                                // if the user submits the form by pressing enter in the field.
                                                e.preventDefault();
                                                jc.$$formSubmit.trigger('click'); // reference the button and click it
                                            });
                                        }
                                    });


                            },
                            },
                            {
                                text: '<span class="fa-solid fa-file-csv"></span> Импортировать ',
                                className: "btn btn-success",
                                enabled: true,
                                action: function(e, dt, node, config) {

                                        $.confirm({
                                            title: 'Добавление пользователей списком',
                                            type: 'green',
                                            content: '' +
                                            '<form action="" name="fileinfo" id="fileinfo" class="formName importfile" enctype="multipart/form-data">' +
                                            '<div class="form-group">' +
                                            '<label>Выберите файл CSV для импорта</label>' +

                                            '<input type="file" class="form-control-file" name="file" id="file">' +
                                            '</div>' +
                                            '</form>',
                                            buttons: {
                                                formSubmit: {
                                                    text: 'Импортировать',
                                                    btnClass: 'btn-blue',
                                                    action: function () {
                                                        var form44 = document.querySelector("#fileinfo");
                                                        var formdata2 = new FormData(form44);
                                                        $.ajax( {url: '/whitelist_file',
                                                            type: 'POST',
                                                            processData: false,
                                                            contentType: false,
                                                            data: formdata2,
                                                            success: function(data_resp) {
                                                                table.ajax.reload();
                                                            },
                                                            error: function(response) {
                                                                console.log(response);
                                                            }
                                                        });

                                                    }
                                                },
                                                cancel: {
                                                    text: 'Отменить',
                                                    btnClass: 'btn-secondary',
                                                    //close
                                                },
                                            },
                                            onContentReady: function () {
                                                // bind to events
                                                var jc = this;
                                                this.$content.find('form').on('submit', function (e) {
                                                    // if the user submits the form by pressing enter in the field.
                                                    e.preventDefault();
                                                    jc.$$formSubmit.trigger('click'); // reference the button and click it
                                                });
                                            }
                                        });
                                }



                    },
                    {

                            text: '<span class="fa-solid fa-trash"></span> Удалить ',
                            className: "btn btn-danger",
                            enabled: false,
                            action: function(e, dt, node, config) {
                                var records = table.rows( { selected: true } ).data();
                                $.confirm({
                                    title: 'Подтвердите действие',
                                    content: 'Вы собираетесь удалить '+records.length + " записей",
                                    type: 'red',
                                    typeAnimated: true,
                                    draggable: true,
                                    buttons: {
                                        confirm: {
                                            text: 'Удалить',
                                            btnClass: 'btn btn-primary',
                                            action: function () {
                                                var list_ids = [];
                                                $.each( records, function( key, value ) {

                                                    $.ajax( {url: '/whitelist/'+value.id,
                                                        type: 'DELETE',
                                                        processData: false,
                                                        contentType: false,
                                                        success: function(data_resp) {
                                                            list_ids.push(value.id);
                                                        }
                                                    });
                                                });
                                                console.log(list_ids)
                                                setTimeout(function(){
                                                  table.ajax.reload();
                                                }, 500);
                                            }
                                        },
                                        cancel:{
                                                text: 'Отменить',
                                                btnClass: 'btn-secondary',
                                                action: function () {

                                                }
                                        },

                                    }
                                });

                            }
                    }
                ]
            },
    }
});

table.on( 'select deselect', function (e, dt, type, indexes) {
    var selectedRows = table.rows( { selected: true } ).count();
    table.button( 2 ).enable( selectedRows >0);
});

} );