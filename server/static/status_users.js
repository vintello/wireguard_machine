$(document).ready(function() {

var table = new DataTable('#status_table', {
    info: true,
    order: [[1, 'desc']],
    stateSave: true,
    ajax: {
        url: '/wireguard_user_status_blank',
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
    processing: true,
    layout: {
        top1Start: {
            buttons: ['colvis']
        }
    }
    });
});

