USE bicycle_thefts_db;

-- ==========================================
-- TEMPORAL ANALYSIS: WHEN DO THEFTS HAPPEN?
-- ==========================================

-- 1. Theft trends by year (2014-2024)
SELECT 
    occ_year,
    COUNT(*) as total_thefts,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM bicycle_thefts), 2) as percentage
FROM bicycle_thefts
WHERE occ_year BETWEEN 2014 AND 2024
GROUP BY occ_year
ORDER BY occ_year;

-- 2. Peak theft months (seasonal patterns)
SELECT 
    occ_month,
    COUNT(*) as theft_count,
    ROUND(AVG(bike_cost), 2) as avg_bike_value
FROM bicycle_thefts
WHERE occ_month IS NOT NULL
GROUP BY occ_month
ORDER BY theft_count DESC;

-- 3. Most dangerous days of the week
SELECT 
    occ_dow as day_of_week,
    COUNT(*) as theft_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM bicycle_thefts WHERE occ_dow IS NOT NULL), 2) as percentage
FROM bicycle_thefts
WHERE occ_dow IS NOT NULL
GROUP BY occ_dow
ORDER BY theft_count DESC;

-- 4. Peak theft hours (when cyclists should be most careful)
SELECT 
    occ_hour as hour_of_day,
    COUNT(*) as theft_count,
    CASE 
        WHEN occ_hour BETWEEN 6 AND 11 THEN 'Morning (6am-12pm)'
        WHEN occ_hour BETWEEN 12 AND 17 THEN 'Afternoon (12pm-6pm)'
        WHEN occ_hour BETWEEN 18 AND 21 THEN 'Evening (6pm-10pm)'
        ELSE 'Night (10pm-6am)'
    END as time_period
FROM bicycle_thefts
WHERE occ_hour IS NOT NULL
GROUP BY occ_hour
ORDER BY theft_count DESC
LIMIT 10;

-- ==========================================
-- GEOGRAPHIC ANALYSIS: WHERE DO THEFTS HAPPEN?
-- ==========================================

-- 5. Top 15 theft hotspot neighborhoods
SELECT 
    premises as neighborhood,
    COUNT(*) as theft_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM bicycle_thefts WHERE premises IS NOT NULL), 2) as percentage,
    COUNT(CASE WHEN status = 'RECOVERED' THEN 1 END) as recovered,
    ROUND(COUNT(CASE WHEN status = 'RECOVERED' THEN 1 END) * 100.0 / COUNT(*), 2) as recovery_rate
FROM bicycle_thefts
WHERE premises IS NOT NULL
GROUP BY premises
ORDER BY theft_count DESC
LIMIT 15;

-- 6. Theft risk by location type (Outside, House, Apartment, etc.)
SELECT 
    location_type,
    COUNT(*) as theft_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM bicycle_thefts WHERE location_type IS NOT NULL), 2) as percentage,
    ROUND(AVG(bike_cost), 2) as avg_bike_value
FROM bicycle_thefts
WHERE location_type IS NOT NULL
GROUP BY location_type
ORDER BY theft_count DESC;

-- 7. Police division performance (which divisions have best recovery rates?)
SELECT 
    division,
    COUNT(*) as total_thefts,
    COUNT(CASE WHEN status = 'RECOVERED' THEN 1 END) as recovered,
    COUNT(CASE WHEN status = 'STOLEN' THEN 1 END) as still_stolen,
    ROUND(COUNT(CASE WHEN status = 'RECOVERED' THEN 1 END) * 100.0 / COUNT(*), 2) as recovery_rate_percent
FROM bicycle_thefts
WHERE division IS NOT NULL
GROUP BY division
ORDER BY recovery_rate_percent DESC;

-- ==========================================
-- BIKE ATTRIBUTES: WHAT BIKES GET STOLEN?
-- ==========================================

-- 8. Most stolen bike makes (brands thieves target)
SELECT 
    bike_make,
    COUNT(*) as times_stolen,
    ROUND(AVG(bike_cost), 2) as avg_value,
    COUNT(CASE WHEN status = 'RECOVERED' THEN 1 END) as recovered,
    ROUND(COUNT(CASE WHEN status = 'RECOVERED' THEN 1 END) * 100.0 / COUNT(*), 2) as recovery_rate
FROM bicycle_thefts
WHERE bike_make IS NOT NULL 
  AND bike_make != ''
  AND bike_make != 'UNKNOWN'
GROUP BY bike_make
ORDER BY times_stolen DESC
LIMIT 15;

-- 9. Most stolen bike colors
SELECT 
    bike_colour,
    COUNT(*) as theft_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM bicycle_thefts WHERE bike_colour IS NOT NULL), 2) as percentage
FROM bicycle_thefts
WHERE bike_colour IS NOT NULL 
  AND bike_colour != ''
GROUP BY bike_colour
ORDER BY theft_count DESC
LIMIT 10;

-- 10. Bike type analysis (Mountain, Road, Electric, etc.)
SELECT 
    bike_type,
    COUNT(*) as theft_count,
    ROUND(AVG(bike_cost), 2) as avg_value,
    MIN(bike_cost) as min_value,
    MAX(bike_cost) as max_value
FROM bicycle_thefts
WHERE bike_type IS NOT NULL 
  AND bike_cost > 0
GROUP BY bike_type
ORDER BY theft_count DESC;

-- 11. High-value bike thefts (bikes over $1000)
SELECT 
    bike_make,
    bike_model,
    bike_type,
    bike_cost,
    occ_year,
    premises as location,
    status
FROM bicycle_thefts
WHERE bike_cost > 1000
ORDER BY bike_cost DESC
LIMIT 20;

-- ==========================================
-- ADVANCED INSIGHTS: COMMUNITY SAFETY PATTERNS
-- ==========================================

-- 12. Risk matrix: Time + Location combinations
SELECT 
    CASE 
        WHEN occ_hour BETWEEN 6 AND 17 THEN 'Daytime (6am-6pm)'
        ELSE 'Evening/Night (6pm-6am)'
    END as time_of_day,
    location_type,
    COUNT(*) as theft_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM bicycle_thefts), 2) as percentage
FROM bicycle_thefts
WHERE occ_hour IS NOT NULL 
  AND location_type IS NOT NULL
GROUP BY time_of_day, location_type
ORDER BY theft_count DESC
LIMIT 15;

-- 13. Seasonal risk by premises type (for cyclist safety apps)
SELECT 
    premises,
    occ_month,
    COUNT(*) as theft_count,
    CASE 
        WHEN occ_month IN ('December', 'January', 'February') THEN 'Winter'
        WHEN occ_month IN ('March', 'April', 'May') THEN 'Spring'
        WHEN occ_month IN ('June', 'July', 'August') THEN 'Summer'
        ELSE 'Fall'
    END as season
FROM bicycle_thefts
WHERE premises IS NOT NULL 
  AND occ_month IS NOT NULL
GROUP BY premises, occ_month, season
HAVING theft_count > 50
ORDER BY theft_count DESC;

-- 14. Year-over-year change analysis (is it getting better or worse?)
SELECT 
    occ_year,
    COUNT(*) as thefts,
    COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY occ_year) as change_from_previous_year,
    ROUND((COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY occ_year)) * 100.0 / 
          LAG(COUNT(*)) OVER (ORDER BY occ_year), 2) as percent_change
FROM bicycle_thefts
WHERE occ_year BETWEEN 2014 AND 2024
GROUP BY occ_year
ORDER BY occ_year;

-- 15. Recovery success factors (what helps bikes get recovered?)
SELECT 
    location_type,
    division,
    COUNT(*) as total_thefts,
    COUNT(CASE WHEN status = 'RECOVERED' THEN 1 END) as recovered,
    ROUND(COUNT(CASE WHEN status = 'RECOVERED' THEN 1 END) * 100.0 / COUNT(*), 2) as recovery_rate
FROM bicycle_thefts
WHERE location_type IS NOT NULL 
  AND division IS NOT NULL
GROUP BY location_type, division
HAVING total_thefts > 50
ORDER BY recovery_rate DESC
LIMIT 20;

-- ==========================================
-- CREATE VIEWS FOR POWER BI (FOR QI)
-- ==========================================

-- View 1: Hourly theft patterns
CREATE OR REPLACE VIEW vw_hourly_thefts AS
SELECT occ_hour, COUNT(*) as theft_count
FROM bicycle_thefts
WHERE occ_hour IS NOT NULL
GROUP BY occ_hour
ORDER BY occ_hour;

-- View 2: Top theft locations
CREATE OR REPLACE VIEW vw_top_locations AS
SELECT premises, COUNT(*) as theft_count,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM bicycle_thefts WHERE premises IS NOT NULL), 2) as percentage,
       COUNT(CASE WHEN status = 'RECOVERED' THEN 1 END) as recovered
FROM bicycle_thefts
WHERE premises IS NOT NULL
GROUP BY premises
ORDER BY theft_count DESC;

-- View 3: Yearly trends
CREATE OR REPLACE VIEW vw_yearly_trends AS
SELECT occ_year, COUNT(*) as total_thefts
FROM bicycle_thefts
WHERE occ_year BETWEEN 2014 AND 2024
GROUP BY occ_year
ORDER BY occ_year;

-- View 4: Monthly patterns
CREATE OR REPLACE VIEW vw_monthly_patterns AS
SELECT occ_month, COUNT(*) as theft_count,
       ROUND(AVG(bike_cost), 2) as avg_bike_value
FROM bicycle_thefts
WHERE occ_month IS NOT NULL
GROUP BY occ_month
ORDER BY theft_count DESC;

-- View 5: Bike brands analysis
CREATE OR REPLACE VIEW vw_bike_brands AS
SELECT bike_make, 
       COUNT(*) as times_stolen,
       ROUND(AVG(bike_cost), 2) as avg_value,
       COUNT(CASE WHEN status = 'RECOVERED' THEN 1 END) as recovered
FROM bicycle_thefts
WHERE bike_make IS NOT NULL AND bike_make != '' AND bike_make != 'UNKNOWN'
GROUP BY bike_make
ORDER BY times_stolen DESC;

-- View 6: Police division performance
CREATE OR REPLACE VIEW vw_division_performance AS
SELECT division,
       COUNT(*) as total_thefts,
       COUNT(CASE WHEN status = 'RECOVERED' THEN 1 END) as recovered,
       ROUND(COUNT(CASE WHEN status = 'RECOVERED' THEN 1 END) * 100.0 / COUNT(*), 2) as recovery_rate
FROM bicycle_thefts
WHERE division IS NOT NULL
GROUP BY division
ORDER BY recovery_rate DESC;

-- ==========================================
-- MASTER TABLE FOR POWER BI (FOR QI)
-- ==========================================
USE bicycle_thefts_db;

CREATE OR REPLACE VIEW vw_master_table AS
SELECT 
    event_unique_id,
    occ_date,
    occ_year,
    occ_month,
    occ_dow,
    occ_hour,
    division,
    premises,
    location_type,
    bike_make,
    bike_model,
    bike_type,
    bike_speed,
    bike_colour,
    bike_cost,
    status,
    latitude,
    longitude,
    
    CASE 
        WHEN UPPER(TRIM(bike_make)) IN ('GI', 'GIANT BICYCLE', 'GIANT') THEN 'GIANT'
        WHEN UPPER(TRIM(bike_make)) IN ('TR', 'TREK BICYCLE', 'TREK') THEN 'TREK'
        WHEN UPPER(TRIM(bike_make)) IN ('NO', 'NORCO') THEN 'NORCO'
        WHEN UPPER(TRIM(bike_make)) IN ('CC', 'CCM') THEN 'CCM'
        WHEN UPPER(TRIM(bike_make)) IN ('SU', 'SUPERCYCLE') THEN 'SUPERCYCLE'
        WHEN UPPER(TRIM(bike_make)) IN ('RA', 'RALEIGH') THEN 'RALEIGH'
        WHEN UPPER(TRIM(bike_make)) IN ('SP', 'SPECIALIZED') THEN 'SPECIALIZED'
        WHEN UPPER(TRIM(bike_make)) IN ('CA', 'CANNONDALE') THEN 'CANNONDALE'
        WHEN UPPER(TRIM(bike_make)) IN ('SC', 'SCHWINN') THEN 'SCHWINN'
        WHEN UPPER(TRIM(bike_make)) IN ('OT', 'OTHER', 'UNKNOWN MAKE', 'UK', '?', '') THEN 'UNKNOWN'
        WHEN bike_make IS NULL THEN 'UNKNOWN'
        ELSE UPPER(TRIM(bike_make))
    END AS bike_make_clean,
    
    CASE 
        WHEN occ_month IN ('December', 'January', 'February') THEN 'Winter'
        WHEN occ_month IN ('March', 'April', 'May') THEN 'Spring'
        WHEN occ_month IN ('June', 'July', 'August') THEN 'Summer'
        WHEN occ_month IN ('September', 'October', 'November') THEN 'Fall'
        ELSE 'Unknown'
    END AS season,
    
    CASE 
        WHEN occ_hour BETWEEN 6 AND 11 THEN 'Morning'
        WHEN occ_hour BETWEEN 12 AND 16 THEN 'Afternoon'
        WHEN occ_hour BETWEEN 17 AND 20 THEN 'Evening'
        ELSE 'Night'
    END AS time_of_day
    
FROM bicycle_thefts;
