alter table steam_games add column if not exists tags text[] not null default '{}';
