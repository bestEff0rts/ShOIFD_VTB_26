"""Дашборд финансовых показателей российских предприятий."""

pip install streamlit

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


@st.cache_data
def load_data(file_path: str) -> pd.DataFrame:
    """Загружает данные из CSV-файла.

    Args:
        file_path: Путь к CSV-файлу.

    Returns:
        DataFrame с загруженными данными.
    """
    df = pd.read_csv(file_path, nrows=100)
    # Приводим числовые колонки к float, заменяя некорректные значения на NaN
    numeric_cols = [
        "lon",
        "lat",
        "B_current_assets",
        "B_cash_equivalents",
        "B_total_equity",
        "B_assets",
        "B_liab",
        "PL_before_tax",
        "PL_net_profit",
        "PL_total",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def main():
    """Главная функция дашборда."""
    st.set_page_config(page_title="Финансовый дашборд", layout="wide")
    st.title("📊 Финансовый дашборд российских предприятий")

    # Загрузка данных
    file_path = "./dfa_result.csv"
    try:
        df = load_data(file_path)
    except FileNotFoundError:
        st.error(f"Файл не найден: {file_path}")
        return
    except Exception as e:
        st.error(f"Ошибка загрузки: {e}")
        return

    if df.empty:
        st.warning("Файл пуст")
        return

    st.success(f"Загружено записей: {len(df)}")

    # Боковая панель с фильтрами
    st.sidebar.header("Фильтры")

    # Фильтр по региону
    if "region" in df.columns:
        regions = ["Все"] + sorted(df["region"].dropna().unique().tolist())
        selected_region = st.sidebar.selectbox("Регион", regions)
        if selected_region != "Все":
            df = df[df["region"] == selected_region]

    # Фильтр по ОКВЭД секции
    if "okved_section" in df.columns:
        okved_sections = ["Все"] + sorted(
            df["okved_section"].dropna().unique().tolist()
        )
        selected_section = st.sidebar.selectbox("ОКВЭД секция", okved_sections)
        if selected_section != "Все":
            df = df[df["okved_section"] == selected_section]

    st.sidebar.markdown("---")
    st.sidebar.info(
        "📌 **Ориентиры:** Москва (55.7558, 37.6173), "
        "Санкт-Петербург (59.9343, 30.3351)"
    )

    # Основные метрики
    st.subheader("📈 Ключевые финансовые показатели")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_assets = df["B_assets"].sum(skipna=True)
        st.metric("Суммарные активы", f"{total_assets:,.0f}")

    with col2:
        total_equity = df["B_total_equity"].sum(skipna=True)
        st.metric("Суммарный капитал", f"{total_equity:,.0f}")

    with col3:
        total_profit = df["PL_net_profit"].sum(skipna=True)
        st.metric("Суммарная чистая прибыль", f"{total_profit:,.0f}")

    with col4:
        companies_count = len(df)
        st.metric("Количество предприятий", f"{companies_count:,}")

    st.markdown("---")

    # Пузырьковая диаграмма на карте
    st.subheader("🗺️ Географическое распределение предприятий")

    # Отфильтровываем записи без координат
    map_df = df.dropna(subset=["lat", "lon"]).copy()

    # ДИАГНОСТИКА: показываем информацию о данных
    with st.expander("🔍 Диагностика данных для карты"):
        st.write(f"Всего предприятий с координатами: {len(map_df)}")
        if len(map_df) > 0:
            st.write("Пример координат (первые 5):")
            st.dataframe(map_df[["lat", "lon", "ogrn", "region"]].head())
            
            # Проверяем доступные метрики
            available_metrics = {
                "B_assets": map_df["B_assets"].notna().sum(),
                "B_current_assets": map_df["B_current_assets"].notna().sum(),
                "B_total_equity": map_df["B_total_equity"].notna().sum(),
                "PL_net_profit": map_df["PL_net_profit"].notna().sum(),
                "PL_before_tax": map_df["PL_before_tax"].notna().sum(),
            }
            st.write("Доступность финансовых показателей:")
            for metric, count in available_metrics.items():
                st.write(f"  - {metric}: {count} записей")
            
            # Проверяем диапазон координат
            st.write(f"Диапазон широты (lat): {map_df['lat'].min():.4f} - {map_df['lat'].max():.4f}")
            st.write(f"Диапазон долготы (lon): {map_df['lon'].min():.4f} - {map_df['lon'].max():.4f}")

    if not map_df.empty:
        # Выбираем метрику для пузырьков
        metric_options = {
            "B_assets": "Активы",
            "B_current_assets": "Оборотные активы",
            "B_total_equity": "Капитал",
            "PL_net_profit": "Чистая прибыль",
            "PL_before_tax": "Прибыль до налогообложения",
        }

        metric_for_size = st.selectbox(
            "Размер пузырька отражает:",
            list(metric_options.keys()),
            format_func=lambda x: metric_options[x],
        )

        # Удаляем строки с NaN в выбранной метрике
        map_df_clean = map_df.dropna(subset=[metric_for_size]).copy()

        st.info(f"Предприятий для отображения: {len(map_df_clean)} из {len(map_df)}")

        if map_df_clean.empty:
            st.warning(
                f"Нет данных с координатами и значением {metric_for_size}\n\n"
                f"Попробуйте выбрать другой показатель."
            )
        else:
            # Для размера пузырька используем абсолютное значение
            # Добавляем минимальный размер для всех точек, чтобы они были видны
            size_values = map_df_clean[metric_for_size].abs()
            
            # Если все значения нулевые, создаем константный размер
            if size_values.sum() == 0:
                size_values = pd.Series([5] * len(map_df_clean), index=map_df_clean.index)
                size_label = "фиксированный размер (все значения = 0)"
            else:
                # Логарифмическое масштабирование для лучшей визуализации
                # Добавляем 1 чтобы избежать log(0)
                size_values = np.log1p(size_values)
                size_label = f"log(1+|{metric_options[metric_for_size]}|)"

            st.write(f"Размер пузырьков: {size_label}")
            st.write(f"Диапазон размеров: {size_values.min():.2f} - {size_values.max():.2f}")

            # Создаем карту с пузырьками
            fig_map = px.scatter_mapbox(
                map_df_clean,
                lat="lat",
                lon="lon",
                size=size_values,
                color="region" if "region" in map_df_clean.columns else None,
                hover_name="ogrn" if "ogrn" in map_df_clean.columns else None,
                hover_data={
                    "inn": True,
                    "region": True,
                    metric_for_size: ":.0f",
                    "lat": False,
                    "lon": False,
                },
                size_max=40,  # Увеличил максимальный размер
                zoom=4,
                height=600,
                title=f"Размер пузырька = {metric_options[metric_for_size]} ({size_label})",
                opacity=0.7,
            )

            # Добавляем маркеры для Москвы и Санкт-Петербурга
            cities = pd.DataFrame(
                {
                    "city": ["Москва", "Санкт-Петербург"],
                    "lat": [55.7558, 59.9343],
                    "lon": [37.6173, 30.3351],
                }
            )

            fig_map.add_trace(
                go.Scattermapbox(
                    lat=cities["lat"],
                    lon=cities["lon"],
                    mode="markers+text",
                    marker=go.scattermapbox.Marker(size=15, color="red"),
                    text=cities["city"],
                    textposition="top right",
                    name="Города-ориентиры",
                    hoverinfo="text",
                )
            )

            # Автоматически центрируем карту по данным точкам
            center_lat = map_df_clean["lat"].mean()
            center_lon = map_df_clean["lon"].mean()
            
            fig_map.update_layout(
                mapbox_style="open-street-map",
                mapbox_center={"lat": center_lat, "lon": center_lon},
                margin={"r": 0, "t": 30, "l": 0, "b": 0},
            )

            st.plotly_chart(fig_map, use_container_width=True)

            # Показываем статистику
            st.caption(
                f"📊 Отображается {len(map_df_clean)} предприятий. "
                f"Размер пузырька = {size_label}. "
                f"Отрицательные значения показываются по модулю."
            )
            
            # Альтернативное отображение: простая точечная карта
            with st.expander("🗺️ Альтернативное отображение (все точки одинакового размера)"):
                fig_simple = px.scatter_mapbox(
                    map_df_clean,
                    lat="lat",
                    lon="lon",
                    color="region" if "region" in map_df_clean.columns else None,
                    hover_name="ogrn" if "ogrn" in map_df_clean.columns else None,
                    hover_data={metric_for_size: ":.0f"},
                    zoom=4,
                    height=500,
                    title="Все предприятия (размер не зависит от показателя)",
                )
                fig_simple.add_trace(
                    go.Scattermapbox(
                        lat=cities["lat"],
                        lon=cities["lon"],
                        mode="markers+text",
                        marker=go.scattermapbox.Marker(size=15, color="red"),
                        text=cities["city"],
                        textposition="top right",
                        name="Города-ориентиры",
                    )
                )
                fig_simple.update_layout(
                    mapbox_style="open-street-map",
                    mapbox_center={"lat": center_lat, "lon": center_lon},
                    margin={"r": 0, "t": 30, "l": 0, "b": 0},
                )
                st.plotly_chart(fig_simple, use_container_width=True)
    else:
        st.warning("⚠️ Нет данных с координатами для отображения на карте")
        st.info(
            "Возможные причины:\n"
            "- В файле отсутствуют колонки 'lat' и 'lon'\n"
            "- Все значения 'lat' и 'lon' равны NaN\n"
            "- Проверьте образец данных в начале файла"
        )

    st.markdown("---")

    # Графики распределения
    st.subheader("📊 Анализ распределения показателей")

    col_ch1, col_ch2 = st.columns(2)

    with col_ch1:
        metric_hist = st.selectbox(
            "Выберите показатель для гистограммы:",
            ["B_assets", "B_total_equity", "PL_net_profit", "B_current_assets"],
            format_func=lambda x: {
                "B_assets": "Активы",
                "B_total_equity": "Капитал",
                "PL_net_profit": "Чистая прибыль",
                "B_current_assets": "Оборотные активы",
            }[x],
            key="hist",
        )
        hist_df = df.dropna(subset=[metric_hist]).copy()
        if not hist_df.empty:
            # Ограничиваем выбросы для лучшей визуализации (99-й перцентиль)
            upper_limit = hist_df[metric_hist].quantile(0.99)
            hist_df_filtered = hist_df[hist_df[metric_hist] <= upper_limit]
            
            fig_hist = px.histogram(
                hist_df_filtered,
                x=metric_hist,
                nbins=50,
                title=f"Распределение {metric_hist} (до 99-го перцентиля)",
                labels={metric_hist: "Значение", "count": "Кол-во предприятий"},
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            st.caption(f"Показаны значения до {upper_limit:,.0f} (99-й перцентиль)")
        else:
            st.info("Нет данных для отображения")

    with col_ch2:
        # Топ-10 по активам
        top_df = df[df["B_assets"] > 0].nlargest(10, "B_assets")[
            ["ogrn", "region", "B_assets"]
        ].dropna(subset=["B_assets"])
        if not top_df.empty:
            # Обрезаем длинные ogrn для читаемости
            top_df["ogrn_short"] = top_df["ogrn"].astype(str).str[-8:]
            fig_bar = px.bar(
                top_df,
                x="ogrn_short",
                y="B_assets",
                color="region",
                title="Топ-10 предприятий по активам",
                labels={"ogrn_short": "ОГРН (последние 8 цифр)", "B_assets": "Активы"},
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Нет данных для топа предприятий")

    st.markdown("---")

    # Таблица с данными
    with st.expander("📋 Просмотр данных"):
        display_cols = [
            c
            for c in [
                "ogrn",
                "region",
                "okved_section",
                "B_assets",
                "B_total_equity",
                "PL_net_profit",
                "lat",
                "lon",
            ]
            if c in df.columns
        ]
        if display_cols:
            # Форматируем числовые колонки для отображения
            display_df = df[display_cols].head(100).copy()
            for col in ["B_assets", "B_total_equity", "PL_net_profit"]:
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(
                        lambda x: f"{x:,.0f}" if pd.notna(x) else ""
                    )
            st.dataframe(display_df)
        else:
            st.dataframe(df.head(100))


if __name__ == "__main__":
    main()
