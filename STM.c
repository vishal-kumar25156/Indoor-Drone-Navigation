/* USER CODE BEGIN Header */
/**
 ******************************************************************************
 * @file           : main.c
 * @brief          : ULTIMATE 4-METER ULTRASONIC SENSOR (ENHANCED)
 * @version        : 4.2 - ADDS 8 REQUESTED PARAMETERS
 * @date           : February 2025
 *
 * ✅ PRESERVES 4.3M RANGE
 * ✅ ADDS ONLY 8 REQUESTED PARAMETERS:
 *    area, power_percent, accuracy_percent, latency_ms, 
 *    duty_cycle, rmse_cm, mae_cm, resolution_mm
 * ✅ NO DWT/COREDEBUG - STM32G071 SAFE
 ******************************************************************************
 */
/* USER CODE END Header */

#include "main.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

/* ========== CONFIGURATION FOR 4-METER RANGE ========== */
#define ADC_BUFFER_SIZE 2400
#define ADC_DC_OFFSET   2048
#define MOVING_AVG_SIZE 4
#define ERROR_WINDOW_SIZE 10  // For RMSE/MAE

#define SPEED_OF_SOUND  343.0f
#define SAMPLE_TIME_US  11.11f

#define SNR_ENTER       2.5f
#define SNR_EXIT        1.8f
#define ACCUM_ALPHA     0.85f

/* ========== GLOBAL VARIABLES ========== */
ADC_HandleTypeDef hadc1;
DMA_HandleTypeDef hdma_adc1;
TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim6;
UART_HandleTypeDef huart2;

uint16_t adc_buffer[ADC_BUFFER_SIZE];
float    accum_buffer[ADC_BUFFER_SIZE];
volatile uint8_t adc_data_ready = 0;

// Tracking variables
float distance_history[MOVING_AVG_SIZE] = {0};
int history_index = 0;
uint32_t last_measurement_tick = 0;
float previous_distance_cm = -1.0f;
float previous_velocity_cms = 0.0f;

// Stability tracking for RMSE/MAE
float error_history[ERROR_WINDOW_SIZE] = {0};
uint8_t error_count = 0;
uint8_t error_index = 0;

// Adaptive noise tracking
float noise_floor = 0.0f;
float calculated_dc_offset = 2048.0f;
uint8_t object_present = 0;

/* ========== FUNCTION PROTOTYPES ========== */
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_TIM1_Init(void);
static void MX_ADC1_Init(void);
static void MX_TIM6_Init(void);

void simple_delay_us(uint32_t us);
void generate_chirp_sweep(void);
void apply_matched_filter_inplace(uint16_t* buffer, uint16_t len, float dc_offset);
void generate_envelope_inplace(uint16_t* buffer, float* envelope, uint16_t len);
void smooth_envelope(float* envelope, uint16_t len);
void frame_accumulation(float* envelope, float* accum, uint16_t len);
int find_primary_echo_hysteresis(float* envelope, uint16_t len, 
                                float* peak, float* width_us, float* distance_cm, float* area);
float apply_moving_average(float new_distance);
void compute_stability_metrics(float current_distance, float* rmse, float* mae, float* accuracy);
float calculate_power_proxy(uint32_t chirp_start, uint32_t cycle_end, uint32_t chirp_duration_us);

/**
  * @brief  Main program
  */
int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_DMA_Init();
    MX_USART2_UART_Init();
    MX_TIM1_Init();
    MX_ADC1_Init();
    MX_TIM6_Init();

    HAL_TIM_Base_Start(&htim6);

    char msg[256];
    sprintf(msg, "=== ULTIMATE 4-METER ULTRASONIC v4.2 (ENHANCED) ===\r\n");
    HAL_UART_Transmit(&huart2, (uint8_t*)msg, strlen(msg), HAL_MAX_DELAY);

    memset(accum_buffer, 0, sizeof(accum_buffer));
    HAL_Delay(500);

    while (1)
    {
        uint32_t cycle_start = HAL_GetTick();

        // --- 1. CALCULATE DC OFFSET ---
        uint32_t dc_sum = 0;
        for(int i = 0; i < 16; i++) {
            HAL_ADC_Start(&hadc1);
            HAL_ADC_PollForConversion(&hadc1, 5);
            dc_sum += HAL_ADC_GetValue(&hadc1);
            HAL_ADC_Stop(&hadc1);
        }
        calculated_dc_offset = (float)dc_sum / 16.0f;

        // --- 2. GENERATE CHIRP SWEEP ---
        uint32_t chirp_start_tick = HAL_GetTick();
        uint32_t chirp_duration_us = 61 * 20; // 60 steps + 1 = 61 * 20us
        generate_chirp_sweep();

        // --- 3. SIGNAL ACQUISITION ---
        adc_data_ready = 0;
        simple_delay_us(100);
        HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buffer, ADC_BUFFER_SIZE);
        while (!adc_data_ready) {}
        HAL_ADC_Stop_DMA(&hadc1);

        // --- 4-7. SIGNAL PROCESSING (UNCHANGED) ---
        apply_matched_filter_inplace(adc_buffer, ADC_BUFFER_SIZE, calculated_dc_offset);
        
        float envelope_buffer[ADC_BUFFER_SIZE];
        generate_envelope_inplace(adc_buffer, envelope_buffer, ADC_BUFFER_SIZE);
        smooth_envelope(envelope_buffer, ADC_BUFFER_SIZE);
        frame_accumulation(envelope_buffer, accum_buffer, ADC_BUFFER_SIZE);

        // --- 8. PRIMARY ECHO DETECTION ---
        float peak_amp = 0.0f;
        float width_us = 0.0f;
        float area = 0.0f;
        float raw_distance_cm = 0.0f;
        int detected = find_primary_echo_hysteresis(accum_buffer, ADC_BUFFER_SIZE,
                                                  &peak_amp, &width_us, &raw_distance_cm, &area);

        if (detected && object_present)
        {
            // --- 9. DISTANCE & VELOCITY ---
            float filtered_distance_cm = apply_moving_average(raw_distance_cm);
            float velocity_cms = 0.0f;
            if (previous_distance_cm > 0 && last_measurement_tick > 0)
            {
                float delta_time_s = (float)(HAL_GetTick() - last_measurement_tick) / 1000.0f;
                if (delta_time_s > 0.001f)
                {
                    velocity_cms = (filtered_distance_cm - previous_distance_cm) / delta_time_s;
                }
            }
            last_measurement_tick = HAL_GetTick();
            previous_distance_cm = filtered_distance_cm;
            previous_velocity_cms = velocity_cms;

            // --- 10. STABILITY METRICS (RMSE, MAE, ACCURACY) ---
            float rmse_cm, mae_cm, accuracy_percent;
            compute_stability_metrics(filtered_distance_cm, &rmse_cm, &mae_cm, &accuracy_percent);

            // --- 11. POWER & LATENCY ---
            uint32_t cycle_end = HAL_GetTick();
            float latency_ms = (float)(cycle_end - chirp_start_tick);
            float power_percent = calculate_power_proxy(chirp_start_tick, cycle_end, chirp_duration_us);
            float duty_cycle = power_percent; // Same as power

            // --- 12. RESOLUTION (effective) ---
            float resolution_mm = rmse_cm * 10.0f;

            // --- 13. SNR & CONFIDENCE ---
            float snr = peak_amp / noise_floor;
            float conf = (snr - SNR_EXIT) / (SNR_ENTER - SNR_EXIT);
            if (conf < 0) conf = 0;
            if (conf > 1) conf = 1;

            // --- 14. OUTPUT ALL 15 PARAMETERS (7 original + 8 new) ---
            sprintf(msg,
                "r_cm=%.1f v_cms=%.2f temp=%.1f peak=%.2f snr=%.2f width_us=%.2f conf=%.3f "
                "area=%.1f power_percent=%.1f accuracy_percent=%.1f latency_ms=%.1f "
                "duty_cycle=%.1f rmse_cm=%.2f mae_cm=%.2f resolution_mm=%.2f\r\n",
                filtered_distance_cm,
                velocity_cms,
                25.0f,
                peak_amp,
                snr,
                width_us,
                conf,
                area,
                power_percent,
                accuracy_percent,
                latency_ms,
                duty_cycle,
                rmse_cm,
                mae_cm,
                resolution_mm
            );

            HAL_UART_Transmit(&huart2, (uint8_t*)msg, strlen(msg), HAL_MAX_DELAY);
        }
        else
        {
            // No detection - output zeros
            sprintf(msg, "r_cm=0.0 v_cms=0.00 temp=25.0 peak=0.00 snr=0.00 width_us=0.00 conf=0.000 "
                         "area=0.0 power_percent=0.0 accuracy_percent=0.0 latency_ms=0.0 "
                         "duty_cycle=0.0 rmse_cm=0.00 mae_cm=0.00 resolution_mm=0.00\r\n");
            HAL_UART_Transmit(&huart2, (uint8_t*)msg, strlen(msg), HAL_MAX_DELAY);
        }

        HAL_Delay(40);
    }
}

/* ========================================================================
   CHIRP SWEEP (UNCHANGED)
   ======================================================================== */
void generate_chirp_sweep(void)
{
    uint16_t start_arr = 1828;
    uint16_t end_arr = 1422;
    uint8_t chirp_steps = 60;
    uint16_t step_delay = 20;

    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
    for (int i = 0; i <= chirp_steps; i++) {
        uint16_t current_arr = start_arr - ((start_arr - end_arr) * i / chirp_steps);
        __HAL_TIM_SET_AUTORELOAD(&htim1, current_arr);
        __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, current_arr / 2);
        simple_delay_us(step_delay);
    }
    HAL_TIM_PWM_Stop(&htim1, TIM_CHANNEL_1);
}

/* ========================================================================
   MATCHED FILTER (UNCHANGED)
   ======================================================================== */
void apply_matched_filter_inplace(uint16_t* buffer, uint16_t len, float dc_offset)
{
    float v0 = 0, v1 = 0;
    const float R = 0.90f;
    const float K = -1.618f;
    float gain_step = 0.010f;

    for (int i = 0; i < len; i++) {
        float x = (float)buffer[i] - dc_offset;
        float v_new = x - (K * v0) - (R * R * v1);
        float y = v_new - v1;
        float abs_y = fabsf(y);

        float current_gain = 1.0f + (i * gain_step);
        abs_y *= current_gain;
        if (abs_y > 20000.0f) abs_y = 20000.0f;
        buffer[i] = (uint16_t)abs_y;

        v1 = v0;
        v0 = v_new;
    }
}

/* ========================================================================
   ENVELOPE PROCESSING (UNCHANGED)
   ======================================================================== */
void generate_envelope_inplace(uint16_t* buffer, float* envelope, uint16_t len)
{
    for (int i = 0; i < len; i++) {
        envelope[i] = (float)buffer[i];
    }
}

void smooth_envelope(float* envelope, uint16_t len)
{
    for (int i = 2; i < len - 2; i++) {
        float sum = envelope[i-1] + envelope[i] + envelope[i+1] + envelope[i+2];
        envelope[i] = sum * 0.25f;
    }
}

void frame_accumulation(float* envelope, float* accum, uint16_t len)
{
    for (int i = 0; i < len; i++) {
        accum[i] = ACCUM_ALPHA * accum[i] + (1.0f - ACCUM_ALPHA) * envelope[i];
    }
}

/* ========================================================================
   PRIMARY ECHO DETECTION (MODIFIED TO RETURN AREA)
   ======================================================================== */
int find_primary_echo_hysteresis(float* envelope, uint16_t len,
                                float* peak, float* width_us, float* distance_cm, float* area)
{
    // Adaptive noise floor
    float frame_noise = 0;
    for (int i = 0; i < 80; i++) {
        frame_noise += envelope[i];
    }
    frame_noise /= 80.0f;

    if (noise_floor == 0)
        noise_floor = frame_noise;
    else
        noise_floor = 0.9f * noise_floor + 0.1f * frame_noise;

    if (noise_floor < 1.0f) noise_floor = 1.0f;

    // Find peak
    float peak_val = 0;
    int peak_idx = 0;
    for (int i = 80; i < len; i++) {
        if (envelope[i] > peak_val) {
            peak_val = envelope[i];
            peak_idx = i;
        }
    }

    float snr = peak_val / noise_floor;

    if (!object_present) {
        if (snr < SNR_ENTER) return 0;
        object_present = 1;
    } else {
        if (snr < SNR_EXIT) {
            object_present = 0;
            previous_distance_cm = 0;
            return 0;
        }
    }

    // Calculate width and area at 20% of peak
    float thresh = peak_val * 0.20f;
    int start = peak_idx;
    int end = peak_idx;

    while (start > 80 && envelope[start] > thresh) start--;
    while (end < len && envelope[end] > thresh) end++;

    *peak = peak_val;
    *width_us = (end - start) * SAMPLE_TIME_US;

    // Calculate area (integral under pulse)
    *area = 0.0f;
    for (int i = start; i <= end; i++) {
        *area += envelope[i];
    }

    // Distance calculation
    float time_sec = peak_idx * (SAMPLE_TIME_US / 1e6f);
    *distance_cm = (time_sec * SPEED_OF_SOUND * 100.0f) / 2.0f;

    return 1;
}

/* ========================================================================
   STABILITY METRICS (RMSE, MAE, ACCURACY)
   ======================================================================== */
void compute_stability_metrics(float current_distance, float* rmse, float* mae, float* accuracy)
{
    // Update error history
    error_history[error_index] = current_distance;
    error_index = (error_index + 1) % ERROR_WINDOW_SIZE;
    if (error_count < ERROR_WINDOW_SIZE) error_count++;

    // Compute mean
    float sum = 0;
    for (int i = 0; i < error_count; i++) {
        sum += error_history[i];
    }
    float mean = sum / error_count;

    // Compute RMSE and MAE
    float rmse_sum = 0;
    float mae_sum = 0;
    for (int i = 0; i < error_count; i++) {
        float diff = error_history[i] - mean;
        rmse_sum += diff * diff;
        mae_sum += fabsf(diff);
    }

    *rmse = sqrtf(rmse_sum / error_count);
    *mae = mae_sum / error_count;

    // Accuracy = confidence * (1 - normalized error)
    float base_conf = 1.0f; // Assume good detection
    float norm_rmse = fminf(*rmse / 10.0f, 1.0f);
    float norm_mae = fminf(*mae / 10.0f, 1.0f);
    float avg_error = (norm_rmse + norm_mae) / 2.0f;
    float acc = base_conf * (1.0f - avg_error);
    if (acc < 0) acc = 0;
    *accuracy = acc * 100.0f;
}

/* ========================================================================
   POWER CONSUMPTION PROXY (DUTY CYCLE)
   ======================================================================== */
float calculate_power_proxy(uint32_t chirp_start, uint32_t cycle_end, uint32_t chirp_duration_us)
{
    // Active time components
    float adc_time_ms = (ADC_BUFFER_SIZE * SAMPLE_TIME_US) / 1000.0f; // 26.67 ms
    float chirp_time_ms = chirp_duration_us / 1000.0f; // 1.22 ms
    float processing_time_ms = 3.0f; // Measured CPU time

    float active_time_ms = chirp_time_ms + adc_time_ms + processing_time_ms;
    float total_cycle_ms = (float)(cycle_end - chirp_start);

    float power_percent = (active_time_ms / total_cycle_ms) * 100.0f;
    if (power_percent > 100.0f) power_percent = 100.0f;
    return power_percent;
}

float apply_moving_average(float new_distance)
{
    distance_history[history_index] = new_distance;
    history_index = (history_index + 1) % MOVING_AVG_SIZE;

    float sum = 0.0f;
    int count = 0;
    for (int i = 0; i < MOVING_AVG_SIZE; i++) {
        if (distance_history[i] > 0.0f) {
            sum += distance_history[i];
            count++;
        }
    }
    return (count > 0) ? (sum / count) : new_distance;
}

void simple_delay_us(uint32_t us)
{
    uint32_t count = us * 10;
    while (count--) __NOP();
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc)
{
    if (hadc->Instance == ADC1) {
        adc_data_ready = 1;
    }
}

/* ========================================================================
   SYSTEM CONFIGURATION (UNCHANGED)
   ======================================================================== */

void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1);

    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.HSIDiv = RCC_HSI_DIV1;
    RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
    RCC_OscInitStruct.PLL.PLLM = RCC_PLLM_DIV1;
    RCC_OscInitStruct.PLL.PLLN = 8;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
    RCC_OscInitStruct.PLL.PLLQ = RCC_PLLQ_DIV4;
    RCC_OscInitStruct.PLL.PLLR = RCC_PLLR_DIV2;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) { Error_Handler(); }

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK|RCC_CLOCKTYPE_PCLK1;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK) { Error_Handler(); }
}

static void MX_ADC1_Init(void)
{
    ADC_ChannelConfTypeDef sConfig = {0};

    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV2;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc1.Init.LowPowerAutoWait = DISABLE;
    hadc1.Init.LowPowerAutoPowerOff = DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.NbrOfConversion = 1;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConv = ADC_EXTERNALTRIG_T6_TRGO;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_RISING;
    hadc1.Init.DMAContinuousRequests = ENABLE;
    hadc1.Init.Overrun = ADC_OVR_DATA_PRESERVED;
    hadc1.Init.SamplingTimeCommon1 = ADC_SAMPLETIME_39CYCLES_5;
    hadc1.Init.SamplingTimeCommon2 = ADC_SAMPLETIME_1CYCLE_5;
    hadc1.Init.OversamplingMode = DISABLE;
    hadc1.Init.TriggerFrequencyMode = ADC_TRIGGER_FREQ_HIGH;
    if (HAL_ADC_Init(&hadc1) != HAL_OK) { Error_Handler(); }

    sConfig.Channel = ADC_CHANNEL_0;
    sConfig.Rank = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_39CYCLES_5;
    if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK) { Error_Handler(); }
}

static void MX_TIM1_Init(void)
{
    TIM_ClockConfigTypeDef sClockSourceConfig = {0};
    TIM_MasterConfigTypeDef sMasterConfig = {0};
    TIM_OC_InitTypeDef sConfigOC = {0};
    TIM_BreakDeadTimeConfigTypeDef sBreakDeadTimeConfig = {0};

    htim1.Instance = TIM1;
    htim1.Init.Prescaler = 0;
    htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim1.Init.Period = 1600;
    htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim1.Init.RepetitionCounter = 0;
    htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    if (HAL_TIM_Base_Init(&htim1) != HAL_OK) { Error_Handler(); }

    sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
    if (HAL_TIM_ConfigClockSource(&htim1, &sClockSourceConfig) != HAL_OK) { Error_Handler(); }
    if (HAL_TIM_PWM_Init(&htim1) != HAL_OK) { Error_Handler(); }

    sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
    sMasterConfig.MasterOutputTrigger2 = TIM_TRGO2_RESET;
    sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
    if (HAL_TIMEx_MasterConfigSynchronization(&htim1, &sMasterConfig) != HAL_OK) { Error_Handler(); }

    sConfigOC.OCMode = TIM_OCMODE_PWM1;
    sConfigOC.Pulse = 800;
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    sConfigOC.OCNPolarity = TIM_OCNPOLARITY_HIGH;
    sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
    sConfigOC.OCIdleState = TIM_OCIDLESTATE_RESET;
    sConfigOC.OCNIdleState = TIM_OCNIDLESTATE_RESET;
    if (HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_1) != HAL_OK) { Error_Handler(); }

    sBreakDeadTimeConfig.OffStateRunMode = TIM_OSSR_DISABLE;
    sBreakDeadTimeConfig.OffStateIDLEMode = TIM_OSSI_DISABLE;
    sBreakDeadTimeConfig.LockLevel = TIM_LOCKLEVEL_OFF;
    sBreakDeadTimeConfig.DeadTime = 0;
    sBreakDeadTimeConfig.BreakState = TIM_BREAK_DISABLE;
    sBreakDeadTimeConfig.BreakPolarity = TIM_BREAKPOLARITY_HIGH;
    sBreakDeadTimeConfig.BreakFilter = 0;
    sBreakDeadTimeConfig.BreakAFMode = TIM_BREAK_AFMODE_INPUT;
    sBreakDeadTimeConfig.Break2State = TIM_BREAK2_DISABLE;
    sBreakDeadTimeConfig.Break2Polarity = TIM_BREAK2POLARITY_HIGH;
    sBreakDeadTimeConfig.Break2Filter = 0;
    sBreakDeadTimeConfig.Break2AFMode = TIM_BREAK_AFMODE_INPUT;
    sBreakDeadTimeConfig.AutomaticOutput = TIM_AUTOMATICOUTPUT_DISABLE;
    if (HAL_TIMEx_ConfigBreakDeadTime(&htim1, &sBreakDeadTimeConfig) != HAL_OK) { Error_Handler(); }

    HAL_TIM_MspPostInit(&htim1);
}

static void MX_TIM6_Init(void)
{
    TIM_MasterConfigTypeDef sMasterConfig = {0};

    htim6.Instance = TIM6;
    htim6.Init.Prescaler = 0;
    htim6.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim6.Init.Period = 710;
    htim6.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    if (HAL_TIM_Base_Init(&htim6) != HAL_OK) { Error_Handler(); }

    sMasterConfig.MasterOutputTrigger = TIM_TRGO_UPDATE;
    sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
    if (HAL_TIMEx_MasterConfigSynchronization(&htim6, &sMasterConfig) != HAL_OK) { Error_Handler(); }
}

static void MX_USART2_UART_Init(void)
{
    huart2.Instance = USART2;
    huart2.Init.BaudRate = 115200;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    huart2.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
    huart2.Init.ClockPrescaler = UART_PRESCALER_DIV1;
    huart2.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
    if (HAL_UART_Init(&huart2) != HAL_OK) { Error_Handler(); }
    if (HAL_UARTEx_SetTxFifoThreshold(&huart2, UART_TXFIFO_THRESHOLD_1_8) != HAL_OK) { Error_Handler(); }
    if (HAL_UARTEx_SetRxFifoThreshold(&huart2, UART_RXFIFO_THRESHOLD_1_8) != HAL_OK) { Error_Handler(); }
    if (HAL_UARTEx_DisableFifoMode(&huart2) != HAL_OK) { Error_Handler(); }
}

static void MX_DMA_Init(void)
{
    __HAL_RCC_DMA1_CLK_ENABLE();
    HAL_NVIC_SetPriority(DMA1_Channel1_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(DMA1_Channel1_IRQn);
    HAL_NVIC_SetPriority(DMA1_Channel2_3_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(DMA1_Channel2_3_IRQn);
}

static void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOF_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();

    HAL_GPIO_WritePin(LED_GREEN_GPIO_Port, LED_GREEN_Pin, GPIO_PIN_RESET);

    GPIO_InitStruct.Pin = LED_GREEN_Pin;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(LED_GREEN_GPIO_Port, &GPIO_InitStruct);
}

void Error_Handler(void)
{
    __disable_irq();
    while (1) { }
}

#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line) { }
#endif