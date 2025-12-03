Feature: Reportes y análisis predictivos generados por IA
  Como agricultor
  Quiero obtener reportes con análisis predictivos
  Para tomar decisiones informadas sobre mis cultivos

  Background:
    Given el servicio de análisis IA está disponible

  Scenario: Predicción de rendimiento con datos válidos
    When envío POST "/api/ai/predict" con JSON:
      """
      {
        "crop": "maiz",
        "area": 3.5,
        "soil_moisture": 20,
        "temperature": 28
      }
      """
    Then la respuesta debe tener código 200
    And el cuerpo debe incluir "predicted_yield"
    And el cuerpo debe incluir "recommended_actions"

  Scenario: Predicción rechazada por datos incompletos
    When envío POST "/api/ai/predict" con JSON:
      """
      { "crop": "maiz" }
      """
    Then la respuesta debe tener código 400
    And el cuerpo debe incluir "missing_required_fields"

  Scenario: Reporte con variaciones históricas
    When envío GET "/api/ai/report?crop=maiz&period=30d"
    Then la respuesta debe tener código 200
    And el cuerpo debe incluir "historical_trends"
    And "yield_projection"

  Scenario: Cultivo no registrado
    When envío GET "/api/ai/report?crop=desconocido&period=30d"
    Then la respuesta debe tener código 404
    And el cuerpo debe incluir "crop_not_found"
