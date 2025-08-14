// AndroidAPIHelper.java - Clase helper para conectar con tu API

package com.tuapp.mes.helpers;

import android.util.Log;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class AndroidAPIHelper {
    
    private static final String TAG = "AndroidAPIHelper";
    private static final String API_URL = "https://tu-sitio-web.com/api/mysql-proxy.php";
    private ExecutorService executor = Executors.newFixedThreadPool(4);
    
    public interface APICallback {
        void onSuccess(JSONObject response);
        void onError(String error);
    }
    
    public void executeQuery(String sql, JSONArray params, APICallback callback) {
        executor.execute(() -> {
            try {
                // Crear objeto JSON para enviar
                JSONObject requestData = new JSONObject();
                requestData.put("sql", sql);
                if (params != null) {
                    requestData.put("params", params);
                }
                
                // Realizar petición HTTP
                URL url = new URL(API_URL);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setRequestProperty("Accept", "application/json");
                conn.setDoOutput(true);
                conn.setConnectTimeout(30000);
                conn.setReadTimeout(30000);
                
                // Enviar datos
                OutputStreamWriter writer = new OutputStreamWriter(conn.getOutputStream());
                writer.write(requestData.toString());
                writer.flush();
                writer.close();
                
                // Leer respuesta
                int responseCode = conn.getResponseCode();
                BufferedReader reader;
                
                if (responseCode == HttpURLConnection.HTTP_OK) {
                    reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                } else {
                    reader = new BufferedReader(new InputStreamReader(conn.getErrorStream()));
                }
                
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }
                reader.close();
                
                // Procesar respuesta
                JSONObject jsonResponse = new JSONObject(response.toString());
                
                if (jsonResponse.getBoolean("success")) {
                    callback.onSuccess(jsonResponse);
                } else {
                    callback.onError(jsonResponse.getString("error"));
                }
                
            } catch (IOException | JSONException e) {
                Log.e(TAG, "Error en API request", e);
                callback.onError("Error de conexión: " + e.getMessage());
            }
        });
    }
    
    // Métodos específicos para tu MES
    
    public void getMateriales(int limit, APICallback callback) {
        String sql = "SELECT numero_parte, codigo_material, especificacion_material, cantidad FROM materiales LIMIT ?";
        JSONArray params = new JSONArray();
        params.put(limit);
        executeQuery(sql, params, callback);
    }
    
    public void getInventarioSMD(APICallback callback) {
        String sql = "SELECT * FROM InventarioRollosSMD WHERE cantidad > 0";
        executeQuery(sql, null, callback);
    }
    
    public void getInventarioIMD(APICallback callback) {
        String sql = "SELECT * FROM InventarioRollosIMD WHERE cantidad > 0";
        executeQuery(sql, null, callback);
    }
    
    public void getInventarioMAIN(APICallback callback) {
        String sql = "SELECT * FROM InventarioRollosMAIN WHERE cantidad > 0";
        executeQuery(sql, null, callback);
    }
    
    public void insertMovimientoInventario(String numeroRollo, String accion, 
                                         int cantidad, String usuario, APICallback callback) {
        String sql = "INSERT INTO movimientos_inventario (numero_rollo, accion, cantidad, usuario, fecha) VALUES (?, ?, ?, ?, NOW())";
        JSONArray params = new JSONArray();
        params.put(numeroRollo);
        params.put(accion);
        params.put(cantidad);
        params.put(usuario);
        executeQuery(sql, params, callback);
    }
    
    public void buscarMaterial(String codigo, APICallback callback) {
        String sql = "SELECT * FROM materiales WHERE codigo_material LIKE ? OR numero_parte LIKE ?";
        JSONArray params = new JSONArray();
        params.put("%" + codigo + "%");
        params.put("%" + codigo + "%");
        executeQuery(sql, params, callback);
    }
}
