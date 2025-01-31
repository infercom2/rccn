BEGIN;

ALTER TABLE subscribers RENAME TO sub;
create table subscribers (
        id              serial primary key,
        msisdn          varchar,
        name            varchar,
        authorized      smallint not null default 0,
        balance         decimal not null default 0.00,
        subscription_status     smallint not null default 0,
        subscription_date       timestamp default current_timestamp,
	location        varchar,
        roaming         smallint not null default 0,
        equipment       varchar,
        package         smallint not null default 0,
        created         timestamp default current_timestamp
);
INSERT INTO subscribers(id,msisdn,name,authorized,balance,subscription_status,
                        subscription_date,location,roaming,equipment,created)
        SELECT id,msisdn,name,authorized,balance,subscription_status,
               subscription_date,location,roaming,equipment,created FROM sub;
DROP TABLE sub;
SELECT pg_catalog.setval(pg_get_serial_sequence('subscribers','id'), (SELECT MAX(id) FROM subscribers)+1);
CREATE TABLE packages (
        id              serial primary key,
        name            varchar not null,
        conf            varchar
);
UPDATE meta SET value='14' WHERE key='db_revision';

COMMIT;
