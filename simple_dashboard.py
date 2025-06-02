#!/usr/bin/env python3
"""
🏟️ Simple MLB Predictions Dashboard
Just displays your beautiful predictions by date - nothing fancy!
"""

import streamlit as st
import pandas as pd
import requests
import psycopg2
from datetime import datetime, timedelta
import sys
import os

# Page config
st.set_page_config(
    page_title="🏟️ MLB Predictions",
    page_icon="⚾",
    layout="wide"
)

class MLBSimpleDashboard:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'sports_analytics_db',
            'user': 'postgres',
            'password': 'Posterwall1!',
            'port': '5432'
        }
    
    def get_games_for_date(self, target_date):
        """Fetch games for specific date"""
        date_str = target_date.strftime('%Y-%m-%d')
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}"
        
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            
            games = []
            if 'dates' in data and data['dates']:
                for game in data['dates'][0]['games']:
                    if game.get('gameType') == 'R':
                        games.append({
                            'away_team': game['teams']['away']['team']['name'],
                            'home_team': game['teams']['home']['team']['name'],
                            'away_id': game['teams']['away']['team']['id'],
                            'home_id': game['teams']['home']['team']['id'],
                            'away_score': game['teams']['away'].get('score'),
                            'home_score': game['teams']['home'].get('score'),
                            'venue': game['venue']['name'],
                            'status': game['status']['detailedState'],
                            'game_time': game.get('gameDate', ''),
                        })
            return games
        except Exception as e:
            st.error(f"Error fetching games: {e}")
            return []
    
    def make_prediction(self, home_team, away_team, home_id, away_id):
        """Generate prediction"""
        try:
            conn = psycopg2.connect(**self.db_config)
            
            query = f"""
            WITH team_recent_performance AS (
                SELECT 
                    g.home_team_id as team_id,
                    AVG(CASE WHEN g.home_score > g.away_score THEN 1.0 ELSE 0.0 END) as win_rate,
                    AVG(g.home_score) as avg_runs_scored,
                    AVG(g.away_score) as avg_runs_allowed,
                    COUNT(*) as games
                FROM games g
                WHERE g.home_team_id IN ({home_id}, {away_id})
                  AND g.official_date >= '2025-04-01'
                  AND g.status_detailed_state = 'Final'
                GROUP BY g.home_team_id
                
                UNION ALL
                
                SELECT 
                    g.away_team_id as team_id,
                    AVG(CASE WHEN g.away_score > g.home_score THEN 1.0 ELSE 0.0 END) as win_rate,
                    AVG(g.away_score) as avg_runs_scored,
                    AVG(g.home_score) as avg_runs_allowed,
                    COUNT(*) as games
                FROM games g  
                WHERE g.away_team_id IN ({home_id}, {away_id})
                  AND g.official_date >= '2025-04-01'
                  AND g.status_detailed_state = 'Final'
                GROUP BY g.away_team_id
            )
            SELECT 
                team_id,
                AVG(win_rate) as recent_win_rate,
                AVG(avg_runs_scored) as recent_runs_scored,
                AVG(avg_runs_allowed) as recent_runs_allowed,
                SUM(games) as total_games
            FROM team_recent_performance
            GROUP BY team_id
            ORDER BY team_id;
            """
            
            team_stats = pd.read_sql(query, conn)
            conn.close()
            
            if len(team_stats) < 2:
                return None
            
            home_stats = team_stats[team_stats['team_id'] == home_id].iloc[0]
            away_stats = team_stats[team_stats['team_id'] == away_id].iloc[0]
            
            # Your proven algorithm
            home_strength = (
                home_stats['recent_win_rate'] * 0.4 +
                (home_stats['recent_runs_scored'] / (home_stats['recent_runs_scored'] + home_stats['recent_runs_allowed'])) * 0.3 +
                0.53 * 0.3
            )
            
            away_strength = (
                away_stats['recent_win_rate'] * 0.4 +
                (away_stats['recent_runs_scored'] / (away_stats['recent_runs_scored'] + away_stats['recent_runs_allowed'])) * 0.3 +
                0.47 * 0.3
            )
            
            strength_diff = home_strength - away_strength
            home_win_prob = 0.53 + (strength_diff * 0.5)
            home_win_prob = max(0.35, min(0.65, home_win_prob))
            
            return {
                'predicted_winner': home_team if home_win_prob > 0.5 else away_team,
                'confidence': max(home_win_prob, 1 - home_win_prob) * 100,
                'home_win_prob': home_win_prob * 100,
                'away_win_prob': (1 - home_win_prob) * 100,
                'home_record': f"{home_stats['recent_win_rate']:.3f}",
                'away_record': f"{away_stats['recent_win_rate']:.3f}",
                'data_games': f"{int(home_stats['total_games'])}H, {int(away_stats['total_games'])}A"
            }
        except:
            return None
    
    def format_game_time(self, game_time_str):
        """Format game time"""
        try:
            if game_time_str:
                dt = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
                return dt.strftime('%I:%M %p ET')
        except:
            pass
        return "TBD"
    
    def get_confidence_emoji(self, confidence):
        """Get emoji for confidence"""
        if confidence >= 60:
            return "🟢"
        elif confidence >= 55:
            return "🟡"
        else:
            return "🔴"
    
    def display_predictions_for_date(self, target_date):
        """Display predictions exactly like your beautiful script output"""
        
        # Header
        st.markdown("---")
        st.markdown(f"# 🏟️ MLB DAILY PREDICTIONS - {target_date.strftime('%A, %B %d, %Y')}")
        st.markdown(f"⚾ **Model Accuracy Target: 56.7%** | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.markdown("---")
        
        # Get games
        games = self.get_games_for_date(target_date)
        
        if not games:
            st.error("❌ No games found for this date")
            return
        
        st.success(f"✅ Found {len(games)} games")
        st.markdown(f"### 🎯 GENERATING PREDICTIONS FOR {len(games)} GAMES")
        
        successful_predictions = 0
        
        # Display each game exactly like your script
        for i, game in enumerate(games, 1):
            st.markdown("---")
            
            # Game info
            game_time = self.format_game_time(game.get('game_time'))
            
            st.markdown(f"**{i}. 🏟️ {game['away_team']} @ {game['home_team']}**")
            st.markdown(f"📅 {game_time} | 🏟️ {game['venue']}")
            
            # Show final score if available
            if (game['status'] == 'Final' and 
                game.get('home_score') is not None and game.get('away_score') is not None):
                home_score = int(game['home_score'])
                away_score = int(game['away_score'])
                winner = game['home_team'] if home_score > away_score else game['away_team']
                st.markdown(f"📊 **FINAL:** {game['away_team']} {away_score} - {home_score} {game['home_team']}")
                st.markdown(f"🏆 **WINNER:** {winner}")
            else:
                st.markdown(f"📊 **STATUS:** {game['status']}")
            
            # Generate and display prediction
            prediction = self.make_prediction(
                game['home_team'], game['away_team'], 
                game['home_id'], game['away_id']
            )
            
            if prediction:
                conf_emoji = self.get_confidence_emoji(prediction['confidence'])
                
                st.markdown(f"{conf_emoji} **PREDICTION:** {prediction['predicted_winner']} ({prediction['confidence']:.1f}%)")
                st.markdown(f"📈 **PROBABILITIES:** {game['home_team']} {prediction['home_win_prob']:.1f}% | {game['away_team']} {prediction['away_win_prob']:.1f}%")
                st.markdown(f"📊 **RECENT RECORDS:** {game['home_team']} {prediction['home_record']} | {game['away_team']} {prediction['away_record']}")
                st.markdown(f"📋 **DATA:** {prediction['data_games']} games")
                
                # Show result if game is final
                if (game['status'] == 'Final' and 
                    game.get('home_score') is not None and game.get('away_score') is not None):
                    actual_winner = game['home_team'] if game['home_score'] > game['away_score'] else game['away_team']
                    was_correct = prediction['predicted_winner'] == actual_winner
                    result_emoji = "✅" if was_correct else "❌"
                    st.markdown(f"{result_emoji} **RESULT:** {'CORRECT!' if was_correct else 'WRONG'}")
                
                successful_predictions += 1
            else:
                st.markdown("❌ **PREDICTION:** Unable to generate (insufficient data)")
        
        # Summary
        st.markdown("---")
        st.markdown("### 📊 PREDICTION SUMMARY")
        st.markdown(f"🎯 **Total Games:** {len(games)}")
        st.markdown(f"✅ **Predictions Generated:** {successful_predictions}")
        st.markdown(f"📈 **Success Rate:** {successful_predictions/len(games)*100:.1f}%")

def main():
    # Title
    st.title("🏟️ MLB Predictions Dashboard")
    st.markdown("*Simple dashboard showing your perfect prediction output*")
    
    # Sidebar date picker
    st.sidebar.header("📅 Select Date")
    
    # Date input
    selected_date = st.sidebar.date_input(
        "Choose date for predictions",
        value=datetime.now().date(),
        min_value=datetime.now().date() - timedelta(days=7),
        max_value=datetime.now().date() + timedelta(days=14)
    )
    
    # Quick date buttons
    st.sidebar.markdown("**Quick Select:**")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("Today"):
            selected_date = datetime.now().date()
            st.rerun()
    
    with col2:
        if st.button("Tomorrow"):
            selected_date = datetime.now().date() + timedelta(days=1)
            st.rerun()
    
    # Yesterday and day after tomorrow
    col3, col4 = st.sidebar.columns(2)
    
    with col3:
        if st.button("Yesterday"):
            selected_date = datetime.now().date() - timedelta(days=1)
            st.rerun()
    
    with col4:
        if st.button("Day After"):
            selected_date = datetime.now().date() + timedelta(days=2)
            st.rerun()
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh"):
        st.rerun()
    
    # Initialize dashboard
    dashboard = MLBSimpleDashboard()
    
    # Display predictions for selected date
    dashboard.display_predictions_for_date(selected_date)
    
    # Footer
    st.markdown("---")
    st.markdown("**🎯 NEXT STEPS:**")
    st.markdown("• Use the date picker to view different dates")
    st.markdown("• Click 'Today' or 'Tomorrow' for quick access")
    st.markdown("• Refresh to get latest game updates")
    st.markdown("---")
    st.markdown("*🏟️ Thanks for using MLB Predictions! ⚾*")

if __name__ == "__main__":
    main()