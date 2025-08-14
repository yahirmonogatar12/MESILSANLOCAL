// MainActivity.java - Ejemplo de uso en Activity Android

package com.tuapp.mes;

import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import com.tuapp.mes.helpers.AndroidAPIHelper;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

public class MainActivity extends AppCompatActivity {
    
    private static final String TAG = "MainActivity";
    private AndroidAPIHelper apiHelper;
    private TextView textViewResults;
    private Button btnMateriales, btnInventarioSMD, btnInventarioIMD;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        // Inicializar helper de API
        apiHelper = new AndroidAPIHelper();
        
        // Inicializar vistas
        textViewResults = findViewById(R.id.textViewResults);
        btnMateriales = findViewById(R.id.btnMateriales);
        btnInventarioSMD = findViewById(R.id.btnInventarioSMD);
        btnInventarioIMD = findViewById(R.id.btnInventarioIMD);
        
        // Configurar listeners
        setupClickListeners();
    }
    
    private void setupClickListeners() {
        
        btnMateriales.setOnClickListener(v -> {
            textViewResults.setText("Cargando materiales...");
            
            apiHelper.getMateriales(10, new AndroidAPIHelper.APICallback() {
                @Override
                public void onSuccess(JSONObject response) {
                    runOnUiThread(() -> {
                        try {
                            JSONArray data = response.getJSONArray("data");
                            StringBuilder result = new StringBuilder("Materiales encontrados:\n\n");
                            
                            for (int i = 0; i < data.length(); i++) {
                                JSONObject material = data.getJSONObject(i);
                                result.append(" ")
                                      .append(material.getString("numero_parte"))
                                      .append(" - ")
                                      .append(material.getString("codigo_material"))
                                      .append("\n")
                                      .append("  Especificación: ")
                                      .append(material.getString("especificacion_material"))
                                      .append("\n")
                                      .append("  Cantidad: ")
                                      .append(material.getInt("cantidad"))
                                      .append("\n\n");
                            }
                            
                            textViewResults.setText(result.toString());
                            
                        } catch (JSONException e) {
                            Log.e(TAG, "Error parsing materials", e);
                            textViewResults.setText("Error procesando datos");
                        }
                    });
                }
                
                @Override
                public void onError(String error) {
                    runOnUiThread(() -> {
                        textViewResults.setText("Error: " + error);
                        Toast.makeText(MainActivity.this, "Error al cargar materiales", Toast.LENGTH_SHORT).show();
                    });
                }
            });
        });
        
        btnInventarioSMD.setOnClickListener(v -> {
            textViewResults.setText("Cargando inventario SMD...");
            
            apiHelper.getInventarioSMD(new AndroidAPIHelper.APICallback() {
                @Override
                public void onSuccess(JSONObject response) {
                    runOnUiThread(() -> {
                        try {
                            JSONArray data = response.getJSONArray("data");
                            int count = response.getInt("count");
                            
                            StringBuilder result = new StringBuilder("Inventario SMD (" + count + " rollos):\n\n");
                            
                            for (int i = 0; i < Math.min(data.length(), 5); i++) { // Mostrar solo 5
                                JSONObject rollo = data.getJSONObject(i);
                                result.append(" Rollo: ")
                                      .append(rollo.getString("numero_rollo"))
                                      .append("\n")
                                      .append("  Material: ")
                                      .append(rollo.getString("codigo_material"))
                                      .append("\n")
                                      .append("  Cantidad: ")
                                      .append(rollo.getInt("cantidad"))
                                      .append("\n\n");
                            }
                            
                            if (data.length() > 5) {
                                result.append("... y ").append(data.length() - 5).append(" más");
                            }
                            
                            textViewResults.setText(result.toString());
                            
                        } catch (JSONException e) {
                            Log.e(TAG, "Error parsing SMD inventory", e);
                            textViewResults.setText("Error procesando inventario SMD");
                        }
                    });
                }
                
                @Override
                public void onError(String error) {
                    runOnUiThread(() -> {
                        textViewResults.setText("Error: " + error);
                        Toast.makeText(MainActivity.this, "Error al cargar inventario SMD", Toast.LENGTH_SHORT).show();
                    });
                }
            });
        });
        
        btnInventarioIMD.setOnClickListener(v -> {
            textViewResults.setText("Cargando inventario IMD...");
            
            apiHelper.getInventarioIMD(new AndroidAPIHelper.APICallback() {
                @Override
                public void onSuccess(JSONObject response) {
                    runOnUiThread(() -> {
                        try {
                            JSONArray data = response.getJSONArray("data");
                            int count = response.getInt("count");
                            
                            textViewResults.setText("Inventario IMD cargado: " + count + " rollos");
                            
                            // Aquí puedes procesar los datos como necesites
                            
                        } catch (JSONException e) {
                            Log.e(TAG, "Error parsing IMD inventory", e);
                            textViewResults.setText("Error procesando inventario IMD");
                        }
                    });
                }
                
                @Override
                public void onError(String error) {
                    runOnUiThread(() -> {
                        textViewResults.setText("Error: " + error);
                        Toast.makeText(MainActivity.this, "Error al cargar inventario IMD", Toast.LENGTH_SHORT).show();
                    });
                }
            });
        });
    }
    
    // Ejemplo de búsqueda de material
    private void buscarMaterial(String codigo) {
        apiHelper.buscarMaterial(codigo, new AndroidAPIHelper.APICallback() {
            @Override
            public void onSuccess(JSONObject response) {
                runOnUiThread(() -> {
                    try {
                        JSONArray data = response.getJSONArray("data");
                        if (data.length() > 0) {
                            JSONObject material = data.getJSONObject(0);
                            String info = "Material encontrado:\n" +
                                         "Número de parte: " + material.getString("numero_parte") + "\n" +
                                         "Código: " + material.getString("codigo_material") + "\n" +
                                         "Especificación: " + material.getString("especificacion_material");
                            textViewResults.setText(info);
                        } else {
                            textViewResults.setText("Material no encontrado");
                        }
                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing search results", e);
                        textViewResults.setText("Error en búsqueda");
                    }
                });
            }
            
            @Override
            public void onError(String error) {
                runOnUiThread(() -> {
                    textViewResults.setText("Error en búsqueda: " + error);
                });
            }
        });
    }
}
