# Attack-02 — MAC Flooding (CAM Table Exhaustion)

> **Autor:** Julio Pujols  
> **Matrícula:** 20250692  
> **Red asignada:** 192.168.92.0/24  
> **Video demostrativo:** <https://youtu.be/I9nblGyHLRA>

-----

## 1. Objetivo del Laboratorio

Demostrar el ataque **MAC Flooding** saturando la tabla CAM del switch con entradas
MAC aleatorias hasta alcanzar su capacidad máxima, forzando el comportamiento
fail-open (modo hub), y mitigarlo con Port Security en un entorno de laboratorio
aislado sobre PNETLab + vIOS-L2.

-----

## 2. Objetivo del Script

`mac_flooding.py` envía frames Ethernet a máxima velocidad con MAC de origen
aleatoria en cada frame. Cada frame distinto genera una nueva entrada en la tabla
CAM del switch hasta agotarla.

### 2.1 Parámetros

|Parámetro     |Descripción                   |Ejemplo|
|--------------|------------------------------|-------|
|`-i / --iface`|Interfaz de red               |`eth0` |
|`-c / --count`|Frames a enviar (0 = infinito)|`10000`|

### 2.2 Requisitos

|Requisito  |Versión     |
|-----------|------------|
|Python     |3.6+        |
|Scapy      |>= 2.4.0    |
|SO         |Linux / Kali|
|Privilegios|root / sudo |

```bash
pip install -r requirements.txt
```

-----

## 3. Funcionamiento del Script

### Flujo de ejecución

```
1. Parseo de argumentos e inicialización de estadísticas
2. Handler SIGINT registrado para salida limpia
3. Bucle principal:
   a. _rand_mac() genera MAC de 6 bytes aleatoria
   b. Ether(src=rand, dst=rand) — frame mínimo Ethernet
   c. sendp() — envío L2 directo (bypassa stack OS)
   d. Estadísticas cada 500 frames
4. Al interrumpir: imprimir totales
```

### Por qué funciona

```
Switch recibe frame → extrae src_mac → busca en CAM
  SI no existe → agrega entrada: src_mac → puerto → timer
  SI tabla llena → fail-open:
    todos los frames unicast se reenvían a todos los puertos
    → tráfico de otros equipos visible en el puerto del atacante
```

-----

## 4. Documentación de la Red

### Topología

```
        R1 (vios-15.5.3M) — 192.168.92.1/24
              |
        SW1 (viosl2-15.2.4.55e)    SW2 (viosl2-15.2.4.55e)
        Gi0/1 ← Attacker (Kali)    Gi0/1 ← Victim2 (VPCS)
        Gi0/2 ← Victim1 (Kali)
        Gi0/3 ── trunk ──────────► SW2 Gi0/0
```

### Direccionamiento e interfaces

|Dispositivo|Interfaz|IP/Máscara         |VLAN  |Rol                  |
|-----------|--------|-------------------|------|---------------------|
|R1         |Gi0/0   |192.168.92.1/24    |10    |Gateway + DHCP server|
|SW1        |Gi0/1   |—                  |10 acc|Puerto atacante      |
|SW1        |Gi0/2   |—                  |10 acc|Puerto Victim1       |
|Attacker   |eth0    |192.168.92.x (DHCP)|10    |Atacante             |
|Victim1    |eth0    |192.168.92.x (DHCP)|10    |Víctima              |

### VLANs

|VLAN |Nombre|Puertos              |
|-----|------|---------------------|
|10   |USERS |SW1 Gi0/0–2 (access) |
|trunk|—     |SW1 Gi0/3 ↔ SW2 Gi0/0|

-----

## 5. Ejecución

### Estado inicial

```
SW1# show mac address-table count
SW1# show mac address-table dynamic
```

### Ejecutar el ataque

```bash
sudo python3 mac_flooding.py -i eth0
```

### Verificar impacto

```
SW1# show mac address-table count
! "Dynamic Address Count" cerca del máximo de la tabla
```

-----

## 6. Contramedida

### Mecanismo

Port Security limita el número de MACs aprendidas por puerto. Al alcanzar el máximo,
el switch aplica la acción de violación configurada: `restrict` descarta frames extras
sin tirar el puerto; `shutdown` err-deshabilita el puerto inmediatamente.

### Configuración en SW1

```
SW1(config)# interface GigabitEthernet0/1
SW1(config-if)# switchport mode access
SW1(config-if)# switchport access vlan 10
SW1(config-if)# switchport port-security
SW1(config-if)# switchport port-security maximum 3
SW1(config-if)# switchport port-security violation restrict
SW1(config-if)# switchport port-security mac-address sticky
SW1(config-if)# end
SW1# write memory
```

### Verificación

```
SW1# show port-security interface Gi0/1
! SecurityViolation sube durante el ataque
! CurrentAddr no supera 3

SW1# show mac address-table count
! Tabla ya no crece más allá del límite
```

-----

## 7. Conclusiones

Al ejecutar el ataque me fijé en cómo la tabla CAM del switch se llenaba a gran velocidad con direcciones MAC aleatorias que yo mismo estaba generando con el script. Comprendí que el problema real no es solo llenar la tabla, sino lo que ocurre después: cuando se agota, el switch entra en modo fail-open y empieza a reenviar el tráfico unicast a todos los puertos como si fuera un hub, lo que permitiría capturar tráfico destinado a otros equipos.

## Cuando configuré Port Security con un máximo de 3 MACs por puerto y la acción restrict, vi cómo el contador de violaciones de seguridad empezaba a subir mientras la tabla dejaba de crecer más allá del límite. Me di cuenta de que Port Security es una de las protecciones más básicas y a la vez más importantes en puertos de acceso, porque corta el ataque de raíz limitando cuántas direcciones MAC puede aprender el switch en cada puerto.

## 8. Referencias

- IEEE 802.1D — MAC Bridges
- Cisco Port Security Configuration Guide
- Scapy Documentation: <https://scapy.readthedocs.io>
