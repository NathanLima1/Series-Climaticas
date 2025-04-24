from data_processing.data_processing import DataProcessing
from training.training import Training
from haversine import haversine, Unit
import folium
import webbrowser
import math
from scipy import stats

class Triangulation:
    def __init__(self):
        self.coordinates  = []
        processed_data = DataProcessing()
        local = processed_data.get_location_coordinates()
        file = open(local)
        aux = []

        for i in file:
            aux.append(i)

        for i in range(len(aux)):
            aux[i] = str(aux[i]).strip('\n')
            self.coordinates.append(aux[i])

        file.close()

        dt_target = []
        dt_cityA = []
        dt_cityB = []
        dt_cityC = []

        for i in range(0, 4):
            dt_target.append(self.coordinates[i])
        for i in range(4,8):
            dt_cityA.append(self.coordinates[i])
        for i in range(8,12):
            dt_cityB.append(self.coordinates[i])
        for i in range(12, 16):
            dt_cityC.append(self.coordinates[i])

        self.tuple_target = (float(dt_target[1]), float(dt_target[2]))
        self.tuple_cityA = (float(dt_cityA[1]), float(dt_cityA[2]))
        self.tuple_cityB = (float(dt_cityB[1]), float(dt_cityB[2]))
        self.tuple_cityC = (float(dt_cityC[1]), float(dt_cityC[2]))
        self.h = [float(self.coordinates[3]), float(self.coordinates[7]), 
                  float(self.coordinates[11]), float(self.coordinates[15])]
        d1 = round(haversine(self.tuple_target, self.tuple_cityA, Unit.KILOMETERS), 4)
        d2 = round(haversine(self.tuple_target, self.tuple_cityB, Unit.KILOMETERS), 4)
        d3 = round(haversine(self.tuple_target, self.tuple_cityC, Unit.KILOMETERS), 4)

        mean = (d1+d2+d3)/3
        self.distance = [d1, d2, d3]

    def idw(self, focus):
        """
        idw = Inverse Distance Weightened
        """
        todo = {
            "Precipitação": 1,
            "Temperatura Máxima": 2,
            "Temperatura Minima": 3 
        }

        data_process = DataProcessing()

        distance = self.distance
        # idw = inverse distance weightened
        self.idw_x = []
        self.idw_y = []
        self.idw_target_y = []

        if focus == 1:
            index = 6
            a = 3
            data = data_process.normalize_data(data_process.load_data_file("Dados comum"))
        elif focus == 2:
            index = 7
            a = 4
            data = data_process.load_data_file("Dados comum")
        elif focus == 3:
            index = 8
            a = 5
            data = data_process("Dados comum")
        
        cont2 = 1

        self.meta_matrix_idw = []
        for i in range(len(data)):
            cont = 0
            sum = 0
            for j in range(index, 15, 3):
                sum += float(data[i][j])/distance[cont]
                cont += 1

            calculate_idw = round(sum/(1/distance[0] + 1/distance[1] + 1/distance[2]), 4)
            aux = []
            aux.append(float(data[i][0]))
            aux.append(float(data[i][1]))
            aux.append(float(data[i][2]))
            aux.append(calculate_idw)

            self.meta_matrix_idw.append(aux) # Matrix for the meta learning

            self.idw_x.append(cont2)
            self.idw_y.append(float(calculate_idw))
            self.idw_target_y.append(float(data[i][a]))

            cont2 += 1

        self.idw_abs_error, self.idw_rel_error = self.calculate_errors(self.idw_y, self.idw_target_y)

    def get_idw(self):
        """
        Returns the variables of the inverse distance weightened
        """
        return self.idw_x, self.idw_y, self.idw_target_y, self.idw_abs_error, self.idw_rel_error, self.meta_matrix_idw

    def avg(self, focus):
        """
        aa = Averaging Arithmetic que virou avg
        """
        data_process = DataProcessing()

        self.avg_x = []
        self.avg_y = []
        self.avg_target_y = []

        if focus == 1:
            index = 6
            a = 3
            data = data_process.normalize_data(data_process.load_data_file("Dados comum"))
        elif focus == 2:
            index = 7
            a = 4
            data = data_process.load_data_file("Dados comum")
        elif focus == 3:
            index = 8
            a = 5
            data = data_process.load_data_file("Dados comum")

        cont = 1
        self.meta_matrix_avg = []

        for i in range(len(data)): # Resolver depois para mais 3 estações vizinhas
            sum = 0
            for j in range(index, 15, 3):
                sum += float(data[i][j])

            avg = (1/3)*sum
            aux = []

            aux.append(float(data[i][0]))
            aux.append(float(data[i][1]))
            aux.append(float(data[i][2]))
            aux.append(avg)
            self.meta_matrix_avg.append(aux)

            self.avg_x.append(cont)
            self.avg_y.append(avg)
            self.avg_target_y.append(float(data[i][a]))

            cont += 1

        self.avg_abs_error, self.avg_rel_error = self.calculate_errors(self.avg_y, self.avg_target_y)

    def get_avg(self):
        """
        Returns the data relative to Averaging Arithmetic
        """
        return self.avg_x, self.avg_y, self.avg_target_y, self.avg_abs_error, self.avg_rel_error, self.meta_matrix_avg

    def show_map(self):
        m = folium.Map(location=self.tupla_tg)
        folium.Marker(location=self.tupla_tg, popup=Popup('Target', show=True)).add_to(m)
        folium.Marker(location=self.tupla_cA, popup=Popup('Vizinha A', show=True)).add_to(m)
        folium.Marker(location=self.tupla_cB, popup=Popup('Vizinha B', show=True)).add_to(m)
        folium.Marker(location=self.tupla_cC, popup=Popup('Vizinha C', show=True)).add_to(m)
        m.save('map.html')
    
        webbrowser.open_new_tab('map.html')

    def oidw(self, focus):
        """
        oidw = Optimized Inverse Distance Weightened
        """
        num_stations = 4  # Number of stations used

        monthly_target_avg = self.generate_monthly_avg(focus, 'target')
        monthly_neighborA_avg = self.generate_monthly_avg(focus, 'VizA')
        monthly_neighborB_avg = self.generate_monthly_avg(focus, 'VizB')
        monthly_neighborC_avg = self.generate_monthly_avg(focus, 'VizC')

        monthly_data = []
        for i in range(len(monthly_target_avg)):
            row = [
                monthly_target_avg[i],
                monthly_neighborA_avg[i],
                monthly_neighborB_avg[i],
                monthly_neighborC_avg[i]
            ]
            monthly_data.append(row)

        if focus == 1:
            index_start = 6
        elif focus == 2:
            index_start = 7
        elif focus == 3:
            index_start = 8

        treatment = DataProcessing()
        raw_data = treatment.load_data_file('Dados comum')

        oidw_results = []
        weighted_sum = 0
        denominator_sum = 0
        month_row_counter = 0
        neighbor_column_counter = 1
        station_counter = 0

        for i in range(len(raw_data)):
            try:
                if raw_data[i][1] != raw_data[i + 1][1]:
                    station_counter = 0
                    neighbor_column_counter = 1

                    for j in range(index_start, 15, 3):
                        weighted_sum += (
                            float(raw_data[i][j]) *
                            monthly_data[month_row_counter][0] *
                            math.log(self.h[0])
                        ) / (
                            self.d[station_counter] +
                            monthly_data[month_row_counter][neighbor_column_counter] *
                            math.log(self.h[neighbor_column_counter])
                        )

                        denominator_sum = 1 / self.d[0] + 1 / self.d[1] + 1 / self.d[2]
                        station_counter += 1
                        neighbor_column_counter += 1

                    oidw_results.append(weighted_sum / denominator_sum)
                    weighted_sum = 0
                    denominator_sum = 0
                    month_row_counter += 1

                else:
                    station_counter = 0
                    neighbor_column_counter = 1

                    for j in range(index_start, 15, 3):
                        weighted_sum += (
                            float(raw_data[i][j]) *
                            monthly_data[month_row_counter][0] *
                            math.log(self.h[0])
                        ) / (
                            self.d[station_counter] +
                            monthly_data[month_row_counter][neighbor_column_counter] *
                            math.log(self.h[neighbor_column_counter])
                        )

                        denominator_sum = 1 / self.d[0] + 1 / self.d[1] + 1 / self.d[2]
                        station_counter += 1
                        neighbor_column_counter += 1

            except IndexError:
                pass

    def rw(self, focus):
        """
        Residual weightening ou ratio weightened?
        """
        num_stations = 3
        monthly_avg_target = self.generate_monthly_average(focus, 'target')
        monthly_avg_vizA = self.generate_monthly_average(focus, 'VizA')
        monthly_avg_vizB = self.generate_monthly_average(focus, 'VizB')
        monthly_avg_vizC = self.generate_monthly_average(focus, 'VizC')

        if focus == 1:
            index = 6
        elif focus == 2:
            index = 7
        elif focus == 3:
            index = 8

        monthly_matrix = []
        self.idw_x = []
        self.idw_y = []
        self.idw_avg_y = []

        for i in range(len(monthly_avg_target)):
            temp = [
                monthly_avg_target[i],
                monthly_avg_vizA[i],
                monthly_avg_vizB[i],
                monthly_avg_vizC[i]
            ]
            monthly_matrix.append(temp)

        treatment = DataProcessing()
        data = treatment.load_data_file('Dados comum')

        current_index = 0
        sum_values = 0
        result = []
        ma_row = 0

        for i in range(len(data)):
            try:
                if i == self.index_end[current_index]:
                    sum_values = (
                        (monthly_matrix[ma_row][0] / monthly_matrix[ma_row][1]) * float(data[i][index]) +
                        (monthly_matrix[ma_row][0] / monthly_matrix[ma_row][2]) * float(data[i][index + 3]) +
                        (monthly_matrix[ma_row][0] / monthly_matrix[ma_row][3]) * float(data[i][index + 6])
                    ) * (1 / 3)
                    result.append(sum_values)
                    sum_values = 0
                    ma_row += 1
                    current_index += 1
                else:
                    sum_values = (
                        (monthly_matrix[ma_row][0] / monthly_matrix[ma_row][1]) * float(data[i][index]) +
                        (monthly_matrix[ma_row][0] / monthly_matrix[ma_row][2]) * float(data[i][index + 3]) +
                        (monthly_matrix[ma_row][0] / monthly_matrix[ma_row][3]) * float(data[i][index + 6])
                    ) * (1 / 3)
                    result.append(sum_values)
                    sum_values = 0
            except IndexError:
                sum_values = (
                    (monthly_matrix[ma_row - 1][0] / monthly_matrix[ma_row - 1][1]) * float(data[i][index]) +
                    (monthly_matrix[ma_row - 1][0] / monthly_matrix[ma_row - 1][2]) * float(data[i][index + 3]) +
                    (monthly_matrix[ma_row - 1][0] / monthly_matrix[ma_row - 1][3]) * float(data[i][index + 6])
                ) * (1 / 3)
                result.append(sum_values)
                sum_values = 0

        self.rw_x = []
        self.rw_y = []
        self.rw_avg_y = []
        self.meta_matrix_rw = []

        x = 0
        for i in range(len(data)):
            self.rw_x.append(x)
            self.rw_y.append(result[i])
            self.rw_avg_y.append(float(data[i][index - 3]))

            temp = [
                float(data[i][0]),
                float(data[i][1]),
                float(data[i][2]),
                float(result[i])
            ]
            self.meta_matrix_rw.append(temp)

            x += 1

        self.rw_abs_error, self.rw_rel_error = self.calculate_errors(self.rw_y, self.rw_avg_y)

    def get_rw(self):
        return self.rw_x, self.rw_y, self.rw_avg_y, self.rw_abs_error, self.rw_rel_error, self.meta_matrix_rw

    def generate_mothly_avg(self, foco, cidade):
        treatment = DataProcessing()
        

        monthly_avg = list()
        self.index_end = list()
        sum = 0
        cont = 2


        if cidade == 'target':
            if foco == 1:
                index = 3 #precipitação na target
                data = treatment.normalize_data(treatment.load_data_file('Dados comum'))
            elif foco == 2:
                index = 4 #Temperatura maxima na target
                data = treatment.load_data_file('Dados comum')
            elif foco == 3:
                index = 5 #Temperatura minima na target
                data = treatment.load_data_file('Dados comum')
        elif cidade == 'VizA':
            if foco == 1:
                index = 6 
                data = treatment.normalize_data(treatment.load_data_file('Dados comum'))
            elif foco == 2:
                index = 7
                data = treatment.load_data_file('Dados comum')
            elif foco == 3:
                index = 8
                data = treatment.load_data_file('Dados comum')
        elif cidade == 'vizB':
            if foco == 1:
                index = 9
                data = treatment.normalize_data(treatment.load_data_file('Dados comum'))
            elif foco == 2:
                index = 10
                data = treatment.load_data_file('Dados comum')
            elif foco == 3:
                index = 11
                data = treatment.load_data_file('Dados comum')
        else:
            if foco == 1:
                index = 12
                data = treatment.normalize_data(treatment.load_data_file('Dados comum'))
            elif foco == 2:
                index = 13
                data = treatment.load_data_file('Dados comum')
            elif foco == 3:
                index = 14
                data = treatment.load_data_file('Dados comum')

        

        #encontar o index da ultima data de cada mes
        for i in range(len(data)):
            try:
                if data[i][1] != data[i+1][1]:
                    self.index_end.append(i)
            except IndexError:
                pass
       
        for i in range(len(data)):
            try:
                if data[i][1] != data[i+1][1]:
                    sum = sum + float(data[i][index])
                    cont = cont + 1
                    monthly_avg.append(sum/cont)
                    sum = 0
                    cont = 1
                else:
                    sum = sum + float(data[i][index])
                    cont = cont + 1

                
            except IndexError:
                pass
        return monthly_avg
    
    def generate_correlation_coefficients(self, focus):
        treatment = DataProcessing()
        normalization = Training()

        if focus == 1:
            index = 3  # Precipitation at target station
            data = normalization.normalize(treatment.load_data_file('Dados comum'))
        elif focus == 2:
            index = 4  # Maximum temperature at target station
            data = treatment.load_data_file('Dados comum')
        elif focus == 3:
            index = 5  # Minimum temperature at target station
            data = treatment.load_data_file('Dados comum')

        coef_target_A = []
        coef_target_B = []
        coef_target_C = []
        days_per_month = []
        day_counter = 0

        values_target = []
        values_station_A = []
        values_station_B = []
        values_station_C = []

        insufficient_days_indices = []

        for i in range(len(data)):
            try:
                if data[i][1] != data[i + 1][1]:
                    values_target.append(float(data[i][index]))
                    values_station_A.append(float(data[i][index + 3]))
                    values_station_B.append(float(data[i][index + 6]))
                    values_station_C.append(float(data[i][index + 9]))
                    day_counter += 1

                    if day_counter >= 2:
                        days_per_month.append(day_counter)
                        day_counter = 0

                        correlation_A = stats.pearsonr(values_target, values_station_A)
                        correlation_B = stats.pearsonr(values_target, values_station_B)
                        correlation_C = stats.pearsonr(values_target, values_station_C)

                        coef_target_A.append(correlation_A[0])
                        coef_target_B.append(correlation_B[0])
                        coef_target_C.append(correlation_C[0])

                        values_target = []
                        values_station_A = []
                        values_station_B = []
                        values_station_C = []
                    else:
                        insufficient_days_indices.append(i)
                else:
                    values_target.append(float(data[i][index]))
                    values_station_A.append(float(data[i][index + 3]))
                    values_station_B.append(float(data[i][index + 6]))
                    values_station_C.append(float(data[i][index + 9]))
                    day_counter += 1

            except IndexError:
                values_target.append(float(data[i - 1][index]))
                values_station_A.append(float(data[i - 1][index + 3]))
                values_station_B.append(float(data[i - 1][index + 6]))
                values_station_C.append(float(data[i - 1][index + 9]))
                day_counter += 1

        return days_per_month, coef_target_A, coef_target_B, coef_target_C

    def onr(self, focus):
        """
        Optimal normalizate ratio?
        """
        treatment = DataProcessing()
        data = treatment.load_data_file('Dados comum')

        days, coef_a, coef_b, coef_c = self.generate_correlation_coef(focus)

        if focus == 1:
            target_index = 6
        elif focus == 2:
            target_index = 7
        elif focus == 3:
            target_index = 8
        else:
            raise ValueError("Invalid focus value. Must be 1, 2, or 3.")

        self.onr_y = []
        result = []
        correlation_counter = 0

        for i in range(len(data)):
            try:
                if data[i][1] != data[i + 1][1]:
                    numerator = (
                        math.pow(coef_a[correlation_counter], 2 * ((days[correlation_counter] - 2) / (1 - coef_a[correlation_counter]))) * float(data[i][target_index]) +
                        math.pow(coef_b[correlation_counter], 2 * ((days[correlation_counter] - 2) / (1 - coef_b[correlation_counter]))) * float(data[i][target_index + 3]) +
                        math.pow(coef_c[correlation_counter], 2 * ((days[correlation_counter] - 2) / (1 - coef_c[correlation_counter]))) * float(data[i][target_index + 6])
                    )

                    denominator = (
                        math.pow(coef_a[correlation_counter], 2 * ((days[correlation_counter] - 2) / (1 - coef_a[correlation_counter]))) +
                        math.pow(coef_b[correlation_counter], 2 * ((days[correlation_counter] - 2) / (1 - coef_b[correlation_counter]))) +
                        math.pow(coef_c[correlation_counter], 2 * ((days[correlation_counter] - 2) / (1 - coef_c[correlation_counter])))
                    )

                    result.append(numerator / denominator)
                    correlation_counter += 1

                else:
                    numerator = (
                        math.pow(coef_a[correlation_counter], 2 * ((days[correlation_counter] - 2) / (1 - coef_a[correlation_counter]))) * float(data[i][target_index]) +
                        math.pow(coef_b[correlation_counter], 2 * ((days[correlation_counter] - 2) / (1 - coef_b[correlation_counter]))) * float(data[i][target_index + 3]) +
                        math.pow(coef_c[correlation_counter], 2 * ((days[correlation_counter] - 2) / (1 - coef_c[correlation_counter]))) * float(data[i][target_index + 6])
                    )

                    denominator = (
                        math.pow(coef_a[correlation_counter], 2 * ((days[correlation_counter] - 2) / (1 - coef_a[correlation_counter]))) +
                        math.pow(coef_b[correlation_counter], 2 * ((days[correlation_counter] - 2) / (1 - coef_b[correlation_counter]))) +
                        math.pow(coef_c[correlation_counter], 2 * ((days[correlation_counter] - 2) / (1 - coef_c[correlation_counter])))
                    )

                    result.append(numerator / denominator)

            except IndexError:
                last = correlation_counter - 1
                numerator = (
                    math.pow(coef_a[last], 2 * ((days[last] - 2) / (1 - coef_a[last]))) * float(data[i][target_index]) +
                    math.pow(coef_b[last], 2 * ((days[last] - 2) / (1 - coef_b[last]))) * float(data[i][target_index + 3]) +
                    math.pow(coef_c[last], 2 * ((days[last] - 2) / (1 - coef_c[last]))) * float(data[i][target_index + 6])
                )

                denominator = (
                    math.pow(coef_a[last], 2 * ((days[last] - 2) / (1 - coef_a[last]))) +
                    math.pow(coef_b[last], 2 * ((days[last] - 2) / (1 - coef_b[last]))) +
                    math.pow(coef_c[last], 2 * ((days[last] - 2) / (1 - coef_c[last])))
                )

                result.append(numerator / denominator)

            except ValueError:
                last = correlation_counter - 1
                numerator = (
                    math.pow(coef_a[last], 2 * ((days[last] - 2) / (1 - coef_a[last]))) * float(data[i][target_index]) +
                    math.pow(coef_b[last], 2 * ((days[last] - 2) / (1 - coef_b[last]))) * float(data[i][target_index + 3]) +
                    math.pow(coef_c[last], 2 * ((days[last] - 2) / (1 - coef_c[last]))) * float(data[i][target_index + 6])
                )

                denominator = (
                    math.pow(coef_a[last], 2 * ((days[last] - 2) / (1 - coef_a[last]))) +
                    math.pow(coef_b[last], 2 * ((days[last] - 2) / (1 - coef_b[last]))) +
                    math.pow(coef_c[last], 2 * ((days[last] - 2) / (1 - coef_c[last])))
                )

                result.append(numerator / denominator)

        self.onr_x = []
        self.onr_alv_y = []
        self.meta_matrix_onr = []

        for index in range(len(data)):
            self.onr_x.append(index)
            self.onr_alv_y.append(float(data[index][target_index - 3]))
            self.onr_y.append(result[index])

            row = [
                float(data[index][0]),
                float(data[index][1]),
                float(data[index][2]),
                float(self.onr_y[index])
            ]
            self.meta_matrix_onr.append(row)

        self.onr_erro_abs, self.onr_erro_rel = self.calcula_erros(self.onr_y, self.onr_alv_y)

    def get_onr(self):
        return self.onr_x, self.onr_y, self.onr_alv_y, self.onr_erro_abs, self.onr_erro_rel, self.meta_matrix_onr


    def calculate_errors(self, real, approx):
        t = Training()
        '''
        exact = t.normalize(real)
        approximate = t.normalize(approx)
        ''' 
        exact = real
        approximate = approx
        sum_ea = 0
        sum_er = 0
        
        for i in range(len(exact)):
            ea = abs(exact[i] - approximate[i])
            er = ea / exact[i]

            sum_ea += ea
            sum_er += er
        
        absolute_error = sum_ea / len(exact)
        relative_error = sum_er / len(exact)

        return absolute_error, relative_error