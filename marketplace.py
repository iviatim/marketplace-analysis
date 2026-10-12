# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

st.set_page_config(page_title="Marketplace Dashboard", layout="wide")

# Настройка темы для более современного вида
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0.8rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .metric-card h3 {
        font-size: 0.9rem;
        margin: 0 0 0.3rem 0;
        font-weight: 500;
    }
    .metric-card h2 {
        font-size: 1.2rem;
        margin: 0;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>📊 Marketplace Analytics Dashboard</h1></div>', unsafe_allow_html=True)

DB_PATH = "marketplace.db"

uploaded_file = st.file_uploader("📁 Загрузите файл отчёта Wildberries или Ozon (Excel)", type=["xlsx"])

def detect_report_type(df):
    wb_cols = {'Вайлдберриз реализовал Товар (Пр)', 'К перечислению Продавцу за реализованный Товар', 'Кол-во', 'Количество возврата'}
    ozon_cols = {'Дата начисления', 'Тип начисления', 'Номер отправления или идентификатор услуги', 'Дата принятия заказа в обработку или оказания услуги',
                 'Склад отгрузки', 'SKU', 'Артикул', 'Название товара или услуги', 'Количество',
                 'За продажу или возврат до вычета комиссий и услуг', 'Ставка комиссии', 'Комиссия за продажу',
                 'Сборка заказа', 'Обработка отправления (Drop-off/Pick-up) (разбивается по товарам пропорционально количеству в отправлении)',
                 'Магистраль', 'Последняя миля (разбивается по товарам пропорционально доле цены товара в сумме отправления)',
                 'Обратная магистраль', 'Обработка возврата', 'Обработка отмененного или невостребованного товара (разбивается по товарам в отправлении в одинаковой пропорции',
                 'Обработка невыкупленного товара', 'Логистика (до 11.05 - плата за доставку КГТ)',
                 'Обратная логистика (до 11.05 - плата за доставку КГТ)', 'Итого'}
    if wb_cols.issubset(df.columns):
        return 'wildberries'
    elif ozon_cols.intersection(df.columns) >= set(['Дата начисления', 'Тип начисления', 'Название товара или услуги', 'Количество', 'Итого']):
        return 'ozon'
    return None

def create_connection():
    return sqlite3.connect(DB_PATH)

def import_to_db(df, table_name):
    conn = create_connection()
    df.to_sql(table_name, conn, index=False, if_exists='replace')
    conn.close()

def get_table_columns(table_name):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cur.fetchall()]
    conn.close()
    return columns

def run_query(query, params=None):
    conn = create_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.write("📋 Первые строки отчёта:")
    st.dataframe(df.head())

    report_type = detect_report_type(df)
    if report_type == 'wildberries':
        table_name = 'wildberries'
        required_columns = [
            'Вайлдберриз реализовал Товар (Пр)',
            'К перечислению Продавцу за реализованный Товар',
            'Кол-во',
            'Количество возврата',
            'Дата продажи',
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"❌ В файле не найден(ы) столбец(ы): {', '.join(missing_columns)}. Проверьте структуру файла.")
            st.stop()
        # Импортируем в БД
        import_to_db(df, table_name)
        # Ввод себестоимости и рекламы
        with st.expander("💰 Настройки расчётов", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                base_cost = st.number_input("Сумма расходов на закупку товаров (руб.)", min_value=0.0, value=0.0, step=0.01)
            with col2:
                ad_spend = st.number_input("Общие расходы на рекламу за период (руб.)", min_value=0.0, value=0.0, step=0.01)
        # Метрики через SQL
        total_sales = run_query(f"SELECT SUM([Вайлдберриз реализовал Товар (Пр)]) as s FROM {table_name}").iloc[0,0] or 0
        total_to_seller = run_query(f"SELECT SUM([К перечислению Продавцу за реализованный Товар]) as s FROM {table_name}").iloc[0,0] or 0
        total_qty = run_query(f"SELECT SUM([Кол-во]) as s FROM {table_name}").iloc[0,0] or 0
        total_returns = run_query(f"SELECT SUM([Количество возврата]) as s FROM {table_name}").iloc[0,0] or 0
        total_base_cost = base_cost
        sales_tax = total_sales * 0.07
        net_profit = total_to_seller - total_base_cost - ad_spend - sales_tax
        # Метрики
        st.subheader("📈 Ключевые показатели")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>💰 Выручка (ВБ)</h3>
                <h2>{total_sales:,.0f} ₽</h2>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>💳 К перечислению</h3>
                <h2>{total_to_seller:,.0f} ₽</h2>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📦 Закупка товаров</h3>
                <h2>{total_base_cost:,.0f} ₽</h2>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📢 Реклама</h3>
                <h2>{ad_spend:,.0f} ₽</h2>
            </div>
            """, unsafe_allow_html=True)
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🏛️ Налог (7%)</h3>
                <h2>{sales_tax:,.0f} ₽</h2>
            </div>
            """, unsafe_allow_html=True)
        with col6:
            profit_color = "🟢" if net_profit > 0 else "🔴"
            st.markdown(f"""
            <div class="metric-card">
                <h3>{profit_color} Чистая прибыль</h3>
                <h2>{net_profit:,.0f} ₽</h2>
            </div>
            """, unsafe_allow_html=True)
        with col7:
            st.markdown(f"""
            <div class="metric-card">
                <h3>✅ Продано</h3>
                <h2>{int(total_qty)} шт.</h2>
            </div>
            """, unsafe_allow_html=True)
        with col8:
            st.markdown(f"""
            <div class="metric-card">
                <h3>↩️ Возвращено</h3>
                <h2>{int(total_returns)} шт.</h2>
            </div>
            """, unsafe_allow_html=True)
        # Диаграммы
        col_pie, col_bar = st.columns(2)
        with col_pie:
            st.subheader("🥧 Продажи и Возвраты")
            pie_data = pd.DataFrame({
                'Категория': ['Продано', 'Возвращено'],
                'Количество': [total_qty, total_returns]
            })
            fig_pie = px.pie(
                pie_data,
                values='Количество',
                names='Категория',
                color_discrete_sequence=['#00D4AA', '#FF6B6B'],
                hole=0.4
            )
            fig_pie.update_traces(
                textposition='inside',
                textinfo='percent+label',
                textfont_size=14,
                marker=dict(line=dict(color='white', width=2))
            )
            fig_pie.update_layout(
                showlegend=False,
                height=400,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_bar:
            st.subheader("🏆 Топ-10 товаров по выручке")
            if 'Название' in get_table_columns(table_name):
                top_items = run_query(f"""
                    SELECT [Название], SUM([Вайлдберриз реализовал Товар (Пр)]) as sales
                    FROM {table_name}
                    WHERE [Вайлдберриз реализовал Товар (Пр)] > 0
                    GROUP BY [Название]
                    ORDER BY sales DESC
                    LIMIT 10
                """)
                if not top_items.empty:
                    fig_bar = px.bar(
                        x=top_items['sales'],
                        y=top_items['Название'],
                        orientation='h',
                        color=top_items['sales'],
                        color_continuous_scale='viridis',
                        title='Топ-10 товаров по выручке'
                    )
                    fig_bar.update_layout(
                        xaxis_title='Выручка, ₽',
                        yaxis_title='Название товара',
                        height=400,
                        showlegend=False,
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    fig_bar.update_traces(
                        marker=dict(line=dict(color='white', width=1))
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.error("❌ В файле отсутствует столбец 'Название'. Топ-10 товаров не может быть построен.")
        # Дополнительная аналитика
        st.subheader("📊 Дополнительная аналитика")
        col_analytics1, col_analytics2 = st.columns(2)
        with col_analytics1:
            if 'Дата продажи' in get_table_columns(table_name):
                daily_sales = run_query(f"""
                    SELECT [Дата продажи], SUM([Вайлдберриз реализовал Товар (Пр)]) as sales
                    FROM {table_name}
                    GROUP BY [Дата продажи]
                    ORDER BY [Дата продажи]
                """)
                daily_sales['Дата продажи'] = pd.to_datetime(daily_sales['Дата продажи'], errors='coerce')
                if daily_sales['Дата продажи'].isna().all():
                    st.info('Не удалось распознать даты в столбце "Дата продажи". Проверьте формат дат в файле.')
                else:
                    daily_sales = daily_sales.dropna(subset=['Дата продажи'])
                    daily_sales['Дата_стр'] = daily_sales['Дата продажи'].dt.strftime('%d.%m.%Y')
                    daily_sales_grouped = daily_sales.groupby('Дата_стр')['sales'].sum().reset_index()
                    fig_line = px.line(
                        daily_sales_grouped,
                        x='Дата_стр',
                        y='sales',
                        title='Динамика продаж по дням',
                        markers=True
                    )
                    fig_line.update_layout(
                        height=300,
                        margin=dict(l=20, r=20, t=40, b=20),
                        xaxis_title='Дата',
                        yaxis_title='Сумма продаж'
                    )
                    st.plotly_chart(fig_line, use_container_width=True)
            elif 'Предмет' in get_table_columns(table_name):
                category_sales = run_query(f"SELECT [Предмет], SUM([Вайлдберриз реализовал Товар (Пр)]) as sales FROM {table_name} GROUP BY [Предмет] ORDER BY sales DESC")
                if not category_sales.empty:
                    fig_category = px.pie(
                        values=category_sales['sales'],
                        names=category_sales['Предмет'],
                        title='Распределение продаж по категориям'
                    )
                    fig_category.update_layout(height=300)
                    st.plotly_chart(fig_category, use_container_width=True)
        with col_analytics2:
            funnel_data = {
                'Этап': ['Выручка ВБ', 'К перечислению', 'После себестоимости', 'После рекламы', 'После налогов', 'Чистая прибыль'],
                'Сумма': [total_sales, total_to_seller, total_to_seller - total_base_cost, 
                         total_to_seller - total_base_cost - ad_spend, 
                         total_to_seller - total_base_cost - ad_spend - sales_tax, net_profit]
            }
            fig_funnel = px.funnel(
                x=funnel_data['Сумма'],
                y=funnel_data['Этап'],
                title='Воронка продаж'
            )
            fig_funnel.update_layout(height=300)
            st.plotly_chart(fig_funnel, use_container_width=True)
        st.subheader("📋 Детализация по товарам")
        required_detail_cols = set(['Название', 'Артикул поставщика', 'Предмет'])
        if required_detail_cols.issubset(get_table_columns(table_name)):
            grouped = run_query(f"""
                SELECT [Название], [Артикул поставщика], [Предмет],
                       SUM([Кол-во]) as [Кол-во],
                       SUM([Количество возврата]) as [Количество возврата],
                       SUM([Вайлдберриз реализовал Товар (Пр)]) as [Вайлдберриз реализовал Товар (Пр)],
                       SUM([К перечислению Продавцу за реализованный Товар]) as [К перечислению Продавцу за реализованный Товар]
                FROM {table_name}
                GROUP BY [Название], [Артикул поставщика], [Предмет]
                ORDER BY [Вайлдберриз реализовал Товар (Пр)] DESC
            """)
            grouped['Прибыль с единицы'] = (grouped['К перечислению Продавцу за реализованный Товар'] / grouped['Кол-во']).round(2)
            grouped['Процент возвратов'] = ((grouped['Количество возврата'] / grouped['Кол-во']) * 100).round(2)
            st.dataframe(
                grouped,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.error("❌ В файле отсутствует один из столбцов: 'Название', 'Артикул поставщика', 'Предмет'. Детализация не может быть построена.")
        st.info("💡 Для более точного учёта себестоимости и рекламы используйте индивидуальные значения по товарам или периодам.")
    elif report_type == 'ozon':
        table_name = 'ozon'
        required_columns = [
            'Дата начисления', 'Тип начисления', 'Название товара или услуги', 'Количество', 'Итого',
            'Комиссия за продажу', 'Магистраль', 'Последняя миля (разбивается по товарам пропорционально доле цены товара в сумме отправления)',
            'Обратная магистраль', 'Обработка возврата'
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"❌ В файле не найден(ы) столбец(ы): {', '.join(missing_columns)}. Проверьте структуру файла.")
            st.stop()
        # Импортируем в БД
        import_to_db(df, table_name)
        with st.expander("💰 Настройки расчётов", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                base_cost = st.number_input("Сумма расходов на закупку товаров (руб.)", min_value=0.0, value=0.0, step=0.01)
            with col2:
                ad_spend = st.number_input("Общие расходы на рекламу за период (руб.)", min_value=0.0, value=0.0, step=0.01)
        # Новый расчет продаж и возвратов
        all_df = run_query(f"SELECT * FROM {table_name}")
        sales_df = all_df[all_df['Итого'] > 0]
        returns_df = all_df[all_df['Итого'] < 0]
        total_sales = sales_df['Итого'].sum()
        total_returns = returns_df['Итого'].sum()  # отрицательное число
        total_qty = sales_df['Количество'].sum()
        total_qty_returns = returns_df['Количество'].sum()  # отрицательное число
        total_commission = all_df['Комиссия за продажу'].sum()
        total_logistics = all_df[['Магистраль',
                                  'Последняя миля (разбивается по товарам пропорционально доле цены товара в сумме отправления)',
                                  'Обратная магистраль',
                                  'Обработка возврата']].sum().sum()
        total_base_cost = base_cost
        net_profit = total_sales + total_returns - total_commission - total_logistics - total_base_cost - ad_spend
        st.subheader("📈 Ключевые показатели (Ozon)")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>\U0001F4B0 Выручка (Ozon)</h3>
                <h2>{total_sales:,.0f} ₽</h2>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>↩️ Возвраты</h3>
                <h2>{total_returns:,.0f} ₽</h2>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📦 Закупка товаров</h3>
                <h2>{total_base_cost:,.0f} ₽</h2>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📢 Реклама</h3>
                <h2>{ad_spend:,.0f} ₽</h2>
            </div>
            """, unsafe_allow_html=True)
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.markdown(f"""
            <div class="metric-card">
                <h3>💸 Комиссия</h3>
                <h2>{total_commission:,.0f} ₽</h2>
            </div>
            """, unsafe_allow_html=True)
        with col6:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🚚 Логистика</h3>
                <h2>{total_logistics:,.0f} ₽</h2>
            </div>
            """, unsafe_allow_html=True)
        with col7:
            profit_color = "🟢" if net_profit > 0 else "🔴"
            st.markdown(f"""
            <div class="metric-card">
                <h3>{profit_color} Чистая прибыль</h3>
                <h2>{net_profit:,.0f} ₽</h2>
            </div>
            """, unsafe_allow_html=True)
        with col8:
            st.markdown(f"""
            <div class="metric-card">
                <h3>✅ Продано</h3>
                <h2>{int(total_qty)} шт.</h2>
            </div>
            """, unsafe_allow_html=True)
        # Диаграммы
        col_pie, col_bar = st.columns(2)
        with col_pie:
            st.subheader("🥧 Продажи и Возвраты")
            pie_data = pd.DataFrame({
                'Категория': ['Продано', 'Возвращено'],
                'Количество': [total_qty, total_qty_returns]
            })
            fig_pie = px.pie(
                pie_data,
                values='Количество',
                names='Категория',
                color_discrete_sequence=['#00D4AA', '#FF6B6B'],
                hole=0.4
            )
            fig_pie.update_traces(
                textposition='inside',
                textinfo='percent+label',
                textfont_size=14,
                marker=dict(line=dict(color='white', width=2))
            )
            fig_pie.update_layout(
                showlegend=False,
                height=400,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_bar:
            st.subheader("🏆 Топ-10 товаров по выручке")
            if 'Название товара или услуги' in get_table_columns(table_name):
                top_items = run_query(f"""
                    SELECT [Название товара или услуги], SUM([Итого]) as s
                    FROM {table_name}
                    WHERE [Итого] > 0
                    GROUP BY [Название товара или услуги]
                    ORDER BY s DESC
                    LIMIT 10
                """)
                if not top_items.empty:
                    fig_bar = px.bar(
                        top_items,
                        x='s',
                        y='Название товара или услуги',
                        orientation='h',
                        color='s',
                        color_continuous_scale='viridis',
                        title='Топ-10 товаров по выручке'
                    )
                    fig_bar.update_layout(
                        xaxis_title='Выручка, ₽',
                        yaxis_title='Название товара',
                        height=400,
                        showlegend=False,
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    fig_bar.update_traces(
                        marker=dict(line=dict(color='white', width=1))
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.error("❌ В файле отсутствует столбец 'Название товара или услуги'. Топ-10 товаров не может быть построен.")
        # Дополнительная аналитика
        st.subheader("�� Дополнительная аналитика")
        col_analytics1, col_analytics2 = st.columns(2)
        with col_analytics1:
            daily_sales = run_query(f"""
                SELECT [Дата начисления], SUM([Итого]) as s
                FROM {table_name}
                WHERE [Итого] > 0
                GROUP BY [Дата начисления]
                ORDER BY [Дата начисления]
            """)
            if 'Дата начисления' in daily_sales.columns:
                daily_sales['Дата начисления'] = pd.to_datetime(daily_sales['Дата начисления'], errors='coerce')
                if daily_sales['Дата начисления'].isna().all():
                    st.info('Не удалось распознать даты в столбце "Дата начисления". Проверьте формат дат в файле.')
                else:
                    daily_sales = daily_sales.dropna(subset=['Дата начисления'])
                    daily_sales['Дата_стр'] = daily_sales['Дата начисления'].dt.strftime('%d.%m.%Y')
                    daily_sales_grouped = daily_sales.groupby('Дата_стр')['s'].sum().reset_index()
                    fig_line = px.line(
                        daily_sales_grouped,
                        x='Дата_стр',
                        y='s',
                        title='Динамика продаж по дням',
                        markers=True
                    )
                    fig_line.update_layout(
                        height=300,
                        margin=dict(l=20, r=20, t=40, b=20),
                        xaxis_title='Дата',
                        yaxis_title='Сумма продаж'
                    )
                    st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("Нет данных о датах начисления для построения графика.")
        with col_analytics2:
            funnel_data = {
                'Этап': ['Выручка', 'Возвраты', 'После себестоимости', 'После рекламы', 'После комиссий и логистики', 'Чистая прибыль'],
                'Сумма': [total_sales, total_returns, total_sales + total_returns - total_base_cost, total_sales + total_returns - total_base_cost - ad_spend, total_sales + total_returns - total_base_cost - ad_spend - total_commission - total_logistics, net_profit]
            }
            fig_funnel = px.funnel(
                x=funnel_data['Сумма'],
                y=funnel_data['Этап'],
                title='Воронка продаж'
            )
            fig_funnel.update_layout(height=300)
            st.plotly_chart(fig_funnel, use_container_width=True)
        st.subheader("📋 Детализация по товарам")
        required_detail_cols = set([
            'Название товара или услуги', 'Артикул', 'Количество', 'Итого',
            'Комиссия за продажу', 'Магистраль',
            'Последняя миля (разбивается по товарам пропорционально доле цены товара в сумме отправления)',
            'Обратная магистраль', 'Обработка возврата'
        ])
        if required_detail_cols.issubset(get_table_columns(table_name)):
            grouped = run_query(f"""
                SELECT [Название товара или услуги], [Артикул],
                       SUM([Количество]) as [Количество],
                       SUM([Итого]) as [Итого],
                       SUM([Комиссия за продажу]) as [Комиссия за продажу],
                       SUM([Магистраль]) as [Магистраль],
                       SUM([Последняя миля (разбивается по товарам пропорционально доле цены товара в сумме отправления)]) as [Последняя миля],
                       SUM([Обратная магистраль]) as [Обратная магистраль],
                       SUM([Обработка возврата]) as [Обработка возврата]
                FROM {table_name}
                WHERE [Итого] > 0
                GROUP BY [Название товара или услуги], [Артикул]
                ORDER BY [Итого] DESC
            """)
            grouped['Себестоимость'] = base_cost * grouped['Количество']
            grouped['Прибыль с единицы'] = ((grouped['Итого'] - grouped['Комиссия за продажу'] - grouped['Магистраль'] - grouped['Последняя миля'] - grouped['Обратная магистраль'] - grouped['Обработка возврата'] - grouped['Себестоимость']) / grouped['Количество']).round(2)
            st.dataframe(
                grouped,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.error("❌ В файле отсутствует один из столбцов для детализации: 'Название товара или услуги', 'Артикул', 'Количество', 'Итого', 'Комиссия за продажу', 'Магистраль', 'Последняя миля', 'Обратная магистраль', 'Обработка возврата'. Детализация не может быть построена.")
        st.info("💡 Для более точного учёта себестоимости и рекламы используйте индивидуальные значения по товарам или периодам.")
    else:
        st.error("❌ Не удалось определить тип отчёта. Проверьте структуру файла.")
else:
    st.warning("⚠️ Пожалуйста, загрузите файл отчёта Wildberries или Ozon в формате .xlsx") 