create schema if not exists `len(fila)` default character set utf8 ;
use `len(fila)`;

create table historico
(
id INTEGER auto_increment,
checkpointAtingido INTEGER NOT NULL,
timestamp INTEGER NOT NULL,

primary key (id)
);