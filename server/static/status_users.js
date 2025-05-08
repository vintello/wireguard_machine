$(document).ready(function() {

var table = new DataTable('#status_table', {
    info: true,
    order: [[1, 'desc']],
    stateSave: true,
    ajax: {
        //url: '/wireguard_user_status_blank',
        url: '/wireguard_user_status',
        type: 'GET',
        dataSrc: 'clients'
    },
    columns: [
        { data: 'name' },
        { data: 'pub_key' },
        { data: 'allowed_ips' },
        { data: 'rx' },
        { data: 'tx' },
        { data: 'last_seen' },
        { data: 'is_online' },
        { data: 'latest_handshake_dt' },
    ],
    select: {
        blurable: true,
        style: 'os'
    },
    createdRow: function( row, data, dataIndex){
                if( data.used === true){
                    $(row).addClass('bg-success');
                }
            },
    processing: true,
    layout: {
        top1Start: {
            buttons: ['colvis',
                {
                    text: '<span class="fa-solid fa-user"></span> Неудаляемый ',
                    className: "btn btn-success",
                    enabled: false,
                    action: function(e, dt, node, config) {
                        var records = table.rows( { selected: true } ).data();
                        $.each(records, function(index, record) {
                            $.ajax( {url: '/wireguard_config_not_removed_flg?config_name=' + encodeURIComponent(record.name),
                                type: 'PUT',
                                success: function(data_resp) {
                                    table.ajax.reload();
                                },
                                error: function(response) {
                                    console.log(response);
                                }
                            });
                            })

                    }
                },
                {
                    text: '<span class="fa-solid fa-trash"></span> Удалить',
                    className: "btn btn-danger delete",
                    enabled: false,
                    action: function(e, dt, node, config) {
                        var records = table.rows( { selected: true } ).data();
                        $.each(records, function(index, record) {
                            if (record.used == true) {
                                $.confirm({
                                    title: 'Удалить пользователя',
                                    content: 'Пользователь <b>' + record.pub_key + '</b> имеет статус неудаляемого. Вы уверены, что хотите удалить его?',
                                    type: 'red',
                                    buttons: {
                                        confirm: {
                                            text: 'Да',
                                            action: function() {
                                                delete_cong_user(record.pub_key);
                                            }
                                        },
                                        cancel: {
                                            text: 'Нет',
                                            action: function() {

                                            }
                                        }
                                    }
                                });
                            } else {
                                delete_cong_user(record.pub_key);
                            }

                        })

                    }
                }
            ]
        },

    }
});

function delete_cong_user(pub_key) {
    $.ajax( {url: '/wireguard_config_remove?pub_key=' + encodeURIComponent(pub_key),
        type: 'DELETE',
        success: function(data_resp) {
            table.ajax.reload();
        },
        error: function(response) {
            console.log(response);
        }
    });
}


table.on( 'select deselect', function (e, dt, type, indexes) {
    var selectedRows = table.rows( { selected: true } ).count();
    table.button( 1 ).enable( selectedRows >0);
    table.button( 2 ).enable( selectedRows >0);
});


});

