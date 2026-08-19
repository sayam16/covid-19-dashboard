export type TrendLabel = "Normal" | "Moderate" | "Surge";

export interface GlobalSeriesPoint {
  date: string;
  new_cases: number;
  cases_ma7: number;
  new_deaths: number;
}

export interface SourceWindow {
  analysis_start: string;
  analysis_end: string;
  daily_feed_start: string;
  daily_feed_end: string;
  weekly_feed_end: string;
  hospital_feed_end: string;
  analysis_mode: string;
}

export interface TopSurgeCountry {
  country: string;
  trend_label: TrendLabel;
  trend_score: number;
  cases_ma7: number;
  growth_rate: number;
}

export interface GlobalSummary {
  latest_date: string;
  total_cases: number;
  total_deaths: number;
  new_cases_last_7d: number;
  new_deaths_last_7d: number;
  countries_tracked: number;
  trend_counts: Record<string, number>;
  top_surge_countries: TopSurgeCountry[];
  global_series: GlobalSeriesPoint[];
  source_window: SourceWindow;
  comparison_window: Record<string, number>;
}

export interface CountryPoint {
  date: string;
  country: string;
  country_code: string;
  who_region?: string;
  new_cases: number;
  cumulative_cases: number;
  new_deaths: number;
  cumulative_deaths: number;
  cases_ma7: number;
  deaths_ma7: number;
  growth_rate: number;
  rolling_trend_14: number;
  surge_ratio: number;
  trend_label: TrendLabel;
  vaccination_coverage_all?: number | null;
  Covid_new_hospitalizations_last_7days?: number | null;
}

export interface CountryResponse {
  country: string;
  start_date: string;
  end_date: string;
  rows: number;
  insights: string[];
  data: CountryPoint[];
}

export interface ForecastPoint {
  date: string;
  predicted_cases: number;
  trend_component: number;
  residual_component: number;
  seasonal_component: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastResponse {
  country: string;
  horizon: number;
  generated_at: string;
  history_end_date: string;
  model_version: string;
  forecast: ForecastPoint[];
  weights: Record<string, number>;
  model_metrics: Record<string, number>;
  feature_importance: Array<{ feature: string; importance: number }>;
  narrative: string;
}

export interface TrendResponse {
  country: string;
  classification: TrendLabel;
  score: number;
  narrative: string;
  latest_date: string;
  drivers: Record<string, string | number | null>;
}

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL;
if (!BASE) {
  throw new Error("NEXT_PUBLIC_API_BASE_URL is not set.");
}

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    next: { revalidate: 180 }
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return response.json();
}

export function fetchCountries() {
  return apiFetch<{ countries: string[] }>("/countries");
}

export function fetchGlobalSummary() {
  return apiFetch<GlobalSummary>("/global-summary");
}

export function fetchCountryData(country: string) {
  return apiFetch<CountryResponse>(`/get-country-data?country=${encodeURIComponent(country)}`);
}

export function fetchTrend(country: string) {
  return apiFetch<TrendResponse>(`/trend?country=${encodeURIComponent(country)}`);
}

export function fetchForecast(country: string, horizon = 14) {
  return apiFetch<ForecastResponse>(
    `/predict?country=${encodeURIComponent(country)}&horizon=${horizon}`
  );
}
