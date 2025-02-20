import os
import time
import pandas as pd
from nba_api.stats.endpoints import teamgamelog, commonteamroster, playergamelog, leaguestandings, teamdetails
from nba_api.stats.static import teams
from requests.exceptions import ConnectionError, Timeout

def retry_request(func, *args, retries=5, delay=10, **kwargs):
    """
    Tenta executar a funcão até um número especificado de tentativas em caso de erro de conexão.
    """
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except (ConnectionError, Timeout) as e:
            print(f"Erro de conexão: {e}. Tentativa {attempt + 1} de {retries}...")
            time.sleep(delay)
    raise Exception(f"Falha após {retries} tentativas.")

def get_team_game_logs(team_id, season):
    print(f"Coletando log de jogos para o time {team_id} na temporada {season}...")
    gamelog = retry_request(teamgamelog.TeamGameLog, team_id=team_id, season=season)
    df_games = gamelog.get_data_frames()[0]
    return df_games

def get_team_roster(team_id, season):
    print(f"Coletando roster para o time {team_id} na temporada {season}...")
    roster = retry_request(commonteamroster.CommonTeamRoster, team_id=team_id, season=season)
    df_roster = roster.get_data_frames()[0]
    return df_roster

def get_player_game_logs(player_id, season):
    print(f"Coletando logs de jogos para o jogador {player_id} na temporada {season}...")
    pgl = retry_request(playergamelog.PlayerGameLog, player_id=player_id, season=season)
    df_pgl = pgl.get_data_frames()[0]
    return df_pgl

def get_player_ids(roster_df, players):
    filtered = roster_df[roster_df['PLAYER'].isin(players)]
    if filtered.empty:
        print("Nenhum jogador encontrado no roster!")
        return {}
    return dict(zip(filtered['PLAYER'], filtered['PLAYER_ID']))

def listar_times_por_conferencia(output_dir="data/raw"):
    """
    Lista todos os times da NBA agrupados por Conferência e salva em um arquivo CSV.
    """
    standings = retry_request(leaguestandings.LeagueStandings)
    df_standings = standings.get_data_frames()[0]

    conferencia_leste = df_standings[df_standings['Conference'] == 'East'][['TeamName', 'TeamID']]
    conferencia_leste['Conferencia'] = 'Leste'

    conferencia_oeste = df_standings[df_standings['Conference'] == 'West'][['TeamName', 'TeamID']]
    conferencia_oeste['Conferencia'] = 'Oeste'

    df_times = pd.concat([conferencia_leste, conferencia_oeste], ignore_index=True)
    df_times.rename(columns={'TeamName': 'Nome', 'TeamID': 'ID'}, inplace=True)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "times_por_conferencia.csv")
    df_times.to_csv(output_path, index=False)
    print(f"Lista de times por conferência salva em: {output_path}")

    return df_times

def obter_classificacao_atual(output_dir="data/raw"):
    """
    Obtém a classificação atual dos times da NBA agrupados por Conferência e salva em um arquivo CSV.
    """
    standings = retry_request(leaguestandings.LeagueStandings)
    df_standings = standings.get_data_frames()[0]
    
    print("Colunas disponíveis em df_standings:", df_standings.columns.tolist())

    columns_required = ['TeamName', 'Conference', 'WinPCT']
    columns_available = [col for col in columns_required if col in df_standings.columns]

    if 'Conference' not in df_standings.columns:
        raise KeyError("A coluna 'Conference' não está disponível no DataFrame retornado.")

    standings_leste = df_standings[df_standings['Conference'] == 'East'][columns_available]
    standings_oeste = df_standings[df_standings['Conference'] == 'West'][columns_available]

    standings_leste['Conferencia'] = 'Leste'
    standings_oeste['Conferencia'] = 'Oeste'

    df_classificacao = pd.concat([standings_leste, standings_oeste], ignore_index=True)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "classificacao_por_conferencia.csv")
    df_classificacao.to_csv(output_path, index=False)
    print(f"Classificação atual por conferência salva em: {output_path}")

    return df_classificacao

def main():
    team_id = 1610612763  # ID do Memphis Grizzlies
    seasons = ['2023-24', '2024-25']
    players = ["Ja Morant", "Desmond Bane", "Jaren Jackson Jr."]

    for season in seasons:
        safe_season = season.replace('/', '-')
        season_dir = os.path.join("data/raw", safe_season)
        team_dir = os.path.join(season_dir, "team")
        players_dir = os.path.join(season_dir, "players")

        os.makedirs(team_dir, exist_ok=True)
        os.makedirs(players_dir, exist_ok=True)

        print(f"\n=== Processando temporada {season} ===")

        team_games = get_team_game_logs(team_id, season)
        team_games_filepath = os.path.join(team_dir, f"games_{safe_season}.csv")
        team_games.to_csv(team_games_filepath, index=False)
        print(f"Dados dos jogos do time salvos em: {team_games_filepath}")
        time.sleep(2)

        roster_df = get_team_roster(team_id, season)
        roster_filepath = os.path.join(team_dir, f"roster_{safe_season}.csv")
        roster_df.to_csv(roster_filepath, index=False)
        print(f"Dados do roster do time salvos em: {roster_filepath}")
        time.sleep(2)

        player_ids = get_player_ids(roster_df, players)

        for player, player_id in player_ids.items():
            pgl_df = get_player_game_logs(player_id, season)
            safe_player = player.replace(' ', '_')
            player_filepath = os.path.join(players_dir, f"{safe_player}_games_{safe_season}.csv")
            pgl_df.to_csv(player_filepath, index=False)
            print(f"Dados dos jogos de {player} salvos em: {player_filepath}")
            time.sleep(3)

    print("\n=== Listando Times por Conferência (RF1) ===")
    listar_times_por_conferencia()

    print("\n=== Obtendo Classificação Atual dos Times (RF2) ===")
    obter_classificacao_atual()

if __name__ == "__main__":
    main()
